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

_SCAN_TIMEOUT = 300.0  # seconds; domain discovery must not hang the worker


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


@register_scanner
class SubfinderScanner(Scanner):
    name = "subfinder"
    category = ScanEngineCategory.SUBDOMAIN_ENUM

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "subfinder",
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

        fd, output_file = tempfile.mkstemp(prefix="subfinder_", suffix=".jsonl")
        os.close(fd)

        cmd = ["subfinder", "-d", hostname, "-oJ", "-o", output_file, "-silent"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_SCAN_TIMEOUT)

            raw_results = await asyncio.to_thread(self._read_jsonl, output_file)
            subdomains = [r.get("host") for r in raw_results if r.get("host")]

            if proc.returncode != 0 and not subdomains:
                err_msg = stderr.decode(errors="replace").strip()[:500]
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=f"subfinder exited {proc.returncode}: {err_msg}",
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )

            desc = f"Subfinder enumeration completed for {hostname}. Discovered {len(subdomains)} subdomains."

            summary = Finding(
                id=uuid.uuid4(),
                title="Subdomain enumeration summary",
                severity=Severity.INFO,
                description=desc,
                engine=self.name,
                matched_at=hostname,
                tags=["recon", "subdomain", "subfinder"],
                metadata={
                    "total_subdomains": len(subdomains),
                    "subdomains": subdomains,
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
            logger.error("subfinder_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"subfinder timed out after {_SCAN_TIMEOUT:.0f}s",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("subfinder_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"subfinder enumeration failed: {exc}",
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


adapter = SubfinderScanner()
