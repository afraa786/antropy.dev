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

_SCAN_TIMEOUT = 300.0  # seconds


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


@register_scanner
class NaabuScanner(Scanner):
    name = "naabu"
    category = ScanEngineCategory.PORT_SCAN

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "naabu",
                "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except (asyncio.TimeoutError, OSError):
            return False

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        hostname = target.hostname

        fd, output_file = tempfile.mkstemp(prefix="naabu_", suffix=".json")
        os.close(fd)

        cmd = [
            "naabu",
            "-host", hostname,
            "-json",
            "-o", output_file,
            "-silent",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=_SCAN_TIMEOUT
            )

            results = await asyncio.to_thread(self._read_results, output_file)

            if proc.returncode != 0 and not results:
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=(
                        f"naabu exited {proc.returncode}: "
                        f"{stderr.decode(errors='replace').strip()[:500]}"
                    ),
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )

            ports = [r.get("port") for r in results if r.get("port")]

            # Convert ports → URLs (useful for downstream tools like HTTPX/Nuclei)
            urls = [f"http://{hostname}:{p}" for p in ports]

            artifacts: dict = {}
            if urls:
                urls_file = await asyncio.to_thread(self._write_urls_file, urls)
                artifacts["urls_file"] = urls_file

            summary = Finding(
                id=uuid.uuid4(),
                title="Open ports discovered",
                severity=Severity.INFO,
                description=(
                    f"Naabu found {len(ports)} open ports on {hostname}."
                ),
                engine=self.name,
                matched_at=hostname,
                tags=["recon", "port_scanner", "naabu"],
                metadata={
                    "total_ports_found": len(ports),
                    "ports": ports,
                    "urls": urls,
                },
            )

            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                findings=[summary],
                success=True,
                started_at=started,
                completed_at=datetime.now(UTC),
                artifacts=artifacts,
            )

        except asyncio.TimeoutError:
            logger.error("naabu_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"naabu timed out after {_SCAN_TIMEOUT:.0f}s",
                started_at=started,
                completed_at=datetime.now(UTC),
            )

        except Exception as exc:
            logger.error("naabu_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"naabu scan failed: {exc}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )

        finally:
            await asyncio.to_thread(_unlink_quiet, output_file)

    @staticmethod
    def _write_urls_file(urls: list[str]) -> str:
        fd, path = tempfile.mkstemp(prefix="naabu_urls_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(urls))
        return path

    @staticmethod
    def _read_results(path: str) -> list[dict]:
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