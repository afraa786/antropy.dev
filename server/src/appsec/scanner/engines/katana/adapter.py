"""Katana adapter for deep web crawling and endpoint discovery.

Runs Katana, parses JSON lines output into summary findings, and publishes
discovered URLs to a temp file for downstream vulnerability engines (like Nuclei).
Output matches the common Finding/ScanResult schema every adapter produces.
"""

import asyncio
import contextlib
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from appsec.scanner.models import Finding, ScanResult, ScanStatus, ScanTarget, Severity
from appsec.scanner.registry import Scanner

logger = structlog.get_logger()

_SCAN_TIMEOUT = 300  # 5 minutes default timeout


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


def _parse_endpoints_file(path: str) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    with contextlib.suppress(json.JSONDecodeError):
                        endpoints.append(json.loads(line))
    return endpoints


class KatanaScanner(Scanner):
    name = "katana"

    async def run(self, target: ScanTarget) -> ScanResult:
        hostname = target.hostname or "unknown"
        target_url = target.target_url

        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp_out:
            output_file = tmp_out.name

        cmd = [
            "katana",
            "-u",
            target_url,
            "-jc",
            "-jsonl",
            "-o",
            output_file,
            "-silent",
        ]

        artifacts: dict[str, Any] = {}

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=_SCAN_TIMEOUT)

            raw_output = stdout_bytes.decode(errors="replace") + stderr_bytes.decode(errors="replace")

            endpoints = await asyncio.to_thread(_parse_endpoints_file, output_file)

            urls = [e.get("endpoint") for e in endpoints if e.get("endpoint")]

            # Publish the crawled URLs as a plain-text list so a downstream vuln engine can ingest them
            urls_file = await asyncio.to_thread(self._write_urls_file, urls)
            artifacts["urls_file"] = urls_file

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
                fingerprint=f"katana:{hostname}:summary",
            )

            return ScanResult(
                scan_job_id=target.scan_job_id,
                status=ScanStatus.COMPLETED,
                findings=[summary],
                raw_output=raw_output,
                artifacts=artifacts,
                completed_at=datetime.now(UTC),
            )
        except TimeoutError:
            logger.error("katana_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                status=ScanStatus.FAILED,
                error=f"Katana scan timed out after {_SCAN_TIMEOUT} seconds.",
                artifacts=artifacts,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("katana_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                status=ScanStatus.FAILED,
                error=f"Katana scan failed: {exc}",
                artifacts=artifacts,
                completed_at=datetime.now(UTC),
            )
        finally:
            await asyncio.to_thread(_unlink_quiet, output_file)

    @staticmethod
    def _write_urls_file(urls: list[str]) -> str:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix="_katana_urls.txt") as tmp:
            for u in urls:
                tmp.write(f"{u}\n")
            return tmp.name
