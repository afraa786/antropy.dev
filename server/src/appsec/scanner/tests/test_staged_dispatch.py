"""Staged dispatcher: proves one stage's artifacts feed the next stage's
Target.options (the katana -> nuclei handoff), and that forwarded temp files
are cleaned up after the run.
"""

import os
import tempfile
import uuid
from datetime import UTC, datetime

import pytest
from appsec.scanner.models import Finding, ScanJob, ScanResult, ScanStatus, ScanTarget, Severity
from appsec.scanner.registry import Scanner, register_scanner
from appsec.scanner.staged_dispatch import staged_dispatch


@register_scanner
class MockKatanaEngine(Scanner):
    name = "katana"

    async def run(self, target: ScanTarget) -> ScanResult:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix="_katana_urls.txt") as tmp:
            tmp.write("https://example.com/api/v1\n")
            tmp_name = tmp.name

        return ScanResult(
            scan_job_id=target.scan_job_id,
            status=ScanStatus.COMPLETED,
            findings=[],
            raw_output="",
            artifacts={"urls_file": tmp_name},
            completed_at=datetime.now(UTC),
        )


@register_scanner
class MockNucleiEngine(Scanner):
    name = "nuclei"

    async def run(self, target: ScanTarget) -> ScanResult:
        urls_file = target.options.get("urls_file")
        finding = Finding(
            id=uuid.uuid4(),
            title="Nuclei Vulnerability Test",
            severity=Severity.HIGH,
            description=f"Scanned using URLs from file: {urls_file}",
            engine=self.name,
            matched_at="example.com",
            fingerprint="nuclei:example.com:test",
        )

        return ScanResult(
            scan_job_id=target.scan_job_id,
            status=ScanStatus.COMPLETED,
            findings=[finding],
            raw_output="",
            artifacts={},
            completed_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_staged_dispatch_katana_then_nuclei():
    job = ScanJob(
        id=uuid.uuid4(),
        target_url="https://example.com",
        engines=["katana", "nuclei"],
        status=ScanStatus.PENDING,
    )

    results = await staged_dispatch(job)

    assert len(results) == 2
    katana_res = next(r for r in results if "katana" in r.artifacts.get("urls_file", ""))
    nuclei_res = next(r for r in results if r.findings and r.findings[0].engine == "nuclei")

    assert katana_res.status == ScanStatus.COMPLETED
    assert nuclei_res.status == ScanStatus.COMPLETED

    urls_file = katana_res.artifacts.get("urls_file")
    assert urls_file is not None

    # Verify that the forwarded temp file is cleaned up after the run.
    assert not os.path.exists(urls_file)  # noqa: ASYNC240
