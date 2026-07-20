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
        out_path = Path(tempfile.gettempdir()) / f"nuclei_{uuid.uuid4()}.json"

        cmd = [
            "nuclei",
            "-u",
            target_url,
            "-jsonl",
            "-o",
            str(out_path),
            "-silent",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(
                    f"Nuclei process exited with code {proc.returncode}: {stderr.decode()}"
                )

            findings = []
            if out_path.exists():
                content = await asyncio.to_thread(
                    out_path.read_text, encoding="utf-8"
                )
                for line in content.splitlines():
                    if line.strip():
                        item = json.loads(line)
                        info = item.get("info", {})
                        findings.append(
                            Finding(
                                id=uuid.uuid4(),
                                title=info.get("name", "Nuclei Match"),
                                severity=Severity.INFO,
                                description=info.get(
                                    "description", "Vulnerability detected."
                                ),
                                engine=self.name,
                                matched_at=hostname,
                                evidence=[line],
                                tags=info.get("tags", ["vulnerability"]),
                                metadata=item,
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
                error_message=f"Nuclei scan failed: {str(exc)}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )


adapter = NucleiScanner()