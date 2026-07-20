import asyncio
import json
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from appsec.scanner.interfaces.models import (
    Finding,
    ScanEngineCategory,
    ScanResult,
    Severity,
    Target,
)
from appsec.scanner.interfaces.registry import register_scanner
from appsec.scanner.interfaces.scanner import Scanner


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
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        hostname = target.hostname

        target_url = f"https://{hostname}"
        out_path = Path(tempfile.gettempdir()) / f"katana_{uuid.uuid4()}.json"

        cmd = ["katana", "-u", target_url, "-jsonl", "-o", str(out_path), "-silent"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"Katana process exited with code {proc.returncode}: {stderr.decode()}"
                )

            endpoints = []
            if out_path.exists():
                content = await asyncio.to_thread(
                    out_path.read_text, encoding="utf-8"
                )
                for line in content.splitlines():
                    if line.strip():
                        data = json.loads(line)
                        endpoints.append(data.get("endpoint", ""))

            findings = []
            if endpoints:
                desc = (
                    f"Katana finished deep crawling. "
                    f"Discovered {len(endpoints)} unique endpoints/links."
                )
                findings.append(
                    Finding(
                        id=uuid.uuid4(),
                        title="Web application crawling summary",
                        severity=Severity.INFO,
                        description=desc,
                        engine=self.name,
                        matched_at=hostname,
                        evidence=endpoints[:20],
                        tags=["crawl", "recon"],
                        metadata={"total_endpoints": len(endpoints)},
                    )
                )

            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                findings=findings,
                success=True,
                started_at=started,
                completed_at=datetime.now(UTC),
            )

        except Exception as exc:
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"Katana scan failed: {str(exc)}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )


adapter = KatanaScanner()