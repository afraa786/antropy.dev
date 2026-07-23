import asyncio
import json
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

_SCAN_TIMEOUT = 600.0  # seconds; deep repository/secret scans must not block workers indefinitely


@register_scanner
class TrufflehogScanner(Scanner):
    name = "trufflehog"
    category = ScanEngineCategory.SECRET_SCAN

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname or target.options.get("git_url"))

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "trufflehog",
                "--version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except (TimeoutError, OSError):
            return False

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        hostname = target.hostname or "git-target"
        git_url = target.options.get("git_url", f"https://{hostname}")

        cmd = ["trufflehog", "git", git_url, "--json", "--no-verification"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_SCAN_TIMEOUT)

            raw_findings = self._parse_json_lines(stdout.decode(errors="replace"))
            findings = self._normalize(raw_findings, hostname)

            if proc.returncode != 0 and not raw_findings:
                err_msg = stderr.decode(errors="replace").strip()[:500]
                return ScanResult(
                    scan_job_id=target.scan_job_id,
                    engine=self.name,
                    success=False,
                    error_message=f"trufflehog exited {proc.returncode}: {err_msg}",
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
            logger.error("trufflehog_scan_timeout", hostname=hostname, timeout=_SCAN_TIMEOUT)
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"trufflehog timed out after {_SCAN_TIMEOUT:.0f}s",
                started_at=started,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("trufflehog_scan_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"trufflehog scan failed: {exc}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )

    @staticmethod
    def _parse_json_lines(output: str) -> list[dict]:
        items: list[dict] = []
        for line in output.splitlines():
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
            detector_name = item.get("DetectorName", "Exposed Secret")
            verified = item.get("Verified", False)
            source_metadata = item.get("SourceMetadata", {}).get("Data", {})

            severity = Severity.HIGH if verified else Severity.MEDIUM

            evidence: list[Evidence] = []
            if item.get("Raw"):
                evidence.append(
                    Evidence(
                        description="Secret match snippet",
                        raw_data=str(item.get("Raw"))[:200],
                    )
                )

            findings.append(
                Finding(
                    id=uuid.uuid4(),
                    title=f"Hardcoded secret detected: {detector_name}",
                    severity=severity,
                    description=f"TruffleHog detected an exposed {detector_name} secret.",
                    engine=self.name,
                    matched_at=hostname,
                    evidence=evidence,
                    tags=["secrets", "trufflehog", detector_name.lower()],
                    metadata={
                        "detector": detector_name,
                        "verified": verified,
                        "source_metadata": source_metadata,
                    },
                )
            )
        return findings


adapter = TrufflehogScanner()
