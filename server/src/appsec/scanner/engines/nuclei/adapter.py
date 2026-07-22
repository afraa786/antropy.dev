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
    Finding,
    ScanEngineCategory,
    ScanResult,
    Severity,
    Target,
)
from appsec.scanner.interfaces.registry import register_scanner
from appsec.scanner.interfaces.scanner import Scanner

logger = get_logger(__name__)

_SCAN_TIMEOUT = 300.0  # seconds; a hung crawl must not block the worker


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


@register_scanner
class KatanaScanner(Scanner):
    name = "katana"
    category = ScanEngineCategory.WEB_CRAWL

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "katana",
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
        target_url = f"https://{hostname}"

        fd, output_file = tempfile.mkstemp(prefix="katana_", suffix=".jsonl")
        os.close(fd)

        # -jc: crawl JavaScript-rendered endpoints (needs the bundled Chromium).
        cmd = ["katana", "-u", target_url, "-jc", "-jsonl", "-o", output_file, "-silent"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_SCAN_TIMEOUT)

            endpoints = await asyncio.to_thread(self._read_endpoints, output_file)

            if proc.returncode != 0 and not endpoints:
                err_msg = stderr.decode(errors="replace").strip()[:500]
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=f"katana exited {proc.returncode}: {err_msg}",
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )

            desc = (
                f"Katana finished deep crawling {target_url}. "
                f"Discovered {len(endpoints)} unique endpoints/links."
            )

            summary = Finding(
                id=uuid.uuid4(),
                title="Web application crawling summary",
                severity=Severity.INFO,
                description=desc,
                engine=self.name,
                matched_at=hostname,
                tags=["recon", "crawler", "katana"],
                metadata={
                    "total_urls_found": len(endpoints),
                    "endpoints": [e.get("endpoint") for e in endpoints if e.get("endpoint")],
                },
            )

            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                findings=[summary],
                success=True,
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except TimeoutError:
            logger.error("katana_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"katana timed out after {_SCAN_TIMEOUT:.0f}s",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("katana_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"katana crawl failed: {exc}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        finally:
            await asyncio.to_thread(_unlink_quiet, output_file)

    @staticmethod
    def _read_endpoints(path: str) -> list[dict]:
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


adapter = KatanaScanner()
