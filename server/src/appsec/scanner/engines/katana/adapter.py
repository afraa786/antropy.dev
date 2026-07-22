"""Katana web-crawler engine. Wraps the `katana` CLI, deep-crawls the target
(including JavaScript endpoints), and emits a normalized crawl-summary finding
plus the discovered endpoint count.

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
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=(
                        f"katana exited {proc.returncode}: {stderr.decode(errors='replace').strip()[:500]}"
                    ),
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )

            urls = [e.get("endpoint") for e in endpoints if e.get("endpoint")]

            # Publish the crawled URLs as a plain-text list so a downstream vuln
            # engine (nuclei) can scan the exact endpoints we discovered. The
            # staged dispatcher forwards `artifacts["urls_file"]` into nuclei's
            # Target.options; it (not katana) owns deleting the file afterwards.
            artifacts: dict = {}
            if urls:
                urls_file = await asyncio.to_thread(self._write_urls_file, urls)
                artifacts["urls_file"] = urls_file

            summary = Finding(
                id=uuid.uuid4(),
                title="Web application crawling summary",
                severity=Severity.INFO,
                description=(
                    f"Katana finished deep crawling {target_url}. "
                    f"Discovered {len(endpoints)} unique endpoints/links."
                ),
                engine=self.name,
                matched_at=hostname,
                tags=["recon", "crawler", "katana"],
                metadata={"total_urls_found": len(endpoints), "endpoints": urls},
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
    def _write_urls_file(urls: list[str]) -> str:
        """Write discovered URLs one-per-line to a persistent temp file and
        return its path. NOT deleted here — the downstream consumer owns it.
        """
        fd, path = tempfile.mkstemp(prefix="katana_urls_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(urls))
        return path

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
