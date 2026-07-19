"""Nuclei vulnerability-scanner engine. Wraps the `nuclei` CLI, runs it against
the target over HTTPS, parses its JSONL output, and emits normalized findings.

Output matches the common Finding/ScanResult schema every adapter produces.
"""

import asyncio
import contextlib
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime

from appsec.logging import get_logger
from appsec.scanner.interfaces.models import (
    Evidence,
    Finding,
    ScanEngineCategory,
    ScanResult,
    Severity,
    Target,
)
from appsec.scanner.interfaces.registry import register_scanner
from appsec.scanner.interfaces.scanner import Scanner

logger = get_logger(__name__)

_SCAN_TIMEOUT = 600.0  # seconds; a hung nuclei run must not block the worker


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


_SEVERITY_MAP = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


@register_scanner
class NucleiScanner(Scanner):
    name = "nuclei"
    category = ScanEngineCategory.VULNERABILITY_SCAN

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nuclei",
                "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except (TimeoutError, OSError):
            return False

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        hostname = target.hostname

        fd, output_file = tempfile.mkstemp(prefix="nuclei_", suffix=".jsonl")
        os.close(fd)

        cmd = ["nuclei", "-jsonl", "-o", output_file, "-silent"]

        # A prior crawl engine may hand us a URL list via options. If present we
        # scan that list; otherwise we scan the target host directly. (The default
        # pipeline runs engines concurrently, so this option is only set when a
        # sequential preset explicitly wires it — direct-target is the norm.)
        url_list = target.options.get("nuclei_url_list")
        if url_list and await asyncio.to_thread(os.path.exists, url_list):
            cmd.extend(["-list", url_list])
        else:
            cmd.extend(["-target", f"https://{hostname}"])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_SCAN_TIMEOUT)

            raw_findings = await asyncio.to_thread(self._read_jsonl, output_file)
            findings = self._normalize(raw_findings, hostname)

            # nuclei exits non-zero on some non-fatal conditions; only treat it as
            # a failure when it produced no parseable output at all.
            if proc.returncode != 0 and not raw_findings:
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=(
                        f"nuclei exited {proc.returncode}: {stderr.decode(errors='replace').strip()[:500]}"
                    ),
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )

            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                findings=findings,
                success=True,
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except TimeoutError:
            logger.error("nuclei_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"nuclei timed out after {_SCAN_TIMEOUT:.0f}s",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("nuclei_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"nuclei execution failed: {exc}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        finally:
            await asyncio.to_thread(_unlink_quiet, output_file)

    @staticmethod
    def _read_jsonl(path: str) -> list[dict]:
        items: list[dict] = []
        if not os.path.exists(path):
            return items
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return items

    def _normalize(self, raw_data: list[dict], hostname: str) -> list[Finding]:
        findings: list[Finding] = []
        for item in raw_data:
            info = item.get("info", {})
            raw_severity = str(info.get("severity", "info")).lower()

            evidence: list[Evidence] = []
            if item.get("matched-at"):
                evidence.append(Evidence(description="Matched URL/endpoint", raw_data=item["matched-at"]))
            if item.get("extracted-results"):
                evidence.append(
                    Evidence(
                        description="Extracted data",
                        raw_data=", ".join(item["extracted-results"]),
                    )
                )

            findings.append(
                Finding(
                    id=uuid.uuid4(),
                    title=info.get("name", "Unknown vulnerability"),
                    severity=_SEVERITY_MAP.get(raw_severity, Severity.INFO),
                    description=info.get("description", "No description provided by engine template."),
                    engine=self.name,
                    matched_at=item.get("matched-at") or hostname,
                    evidence=evidence,
                    tags=[*info.get("tags", []), "nuclei"],
                    metadata={
                        "template_id": item.get("template-id"),
                        "type": item.get("type"),
                        "classification": info.get("classification", {}),
                        "remediation": info.get("remediation"),
                    },
                )
            )
        return findings
