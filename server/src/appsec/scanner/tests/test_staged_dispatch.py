"""Staged dispatcher: proves one stage's artifacts feed the next stage's
Target.options (the katana -> nuclei handoff), and that forwarded temp files
are cleaned up after the run.
"""

import os
import tempfile
import uuid
from datetime import UTC, datetime

import pytest

from appsec.scanner.interfaces.models import (
    Finding,
    ScanResult,
    Severity,
    Target,
)
from appsec.scanner.interfaces.registry import register_scanner
from appsec.scanner.interfaces.scanner import Scanner
from appsec.scanner.staged_dispatch import staged_dispatch


@register_scanner
class MockKatanaEngine(Scanner):
    name = "mock_katana"

    async def validate(self, target: Target) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix="_katana_urls.txt") as tmp:
            tmp.write("https://example.com/api/v1\n")
            tmp_name = tmp.name

        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=self.name,
            success=True,
            findings=[],
            raw_output="",
            artifacts={"urls_file": tmp_name},
            started_at=started,
            completed_at=datetime.now(UTC),
        )


@register_scanner
class MockNucleiEngine(Scanner):
    name = "mock_nuclei"

    async def validate(self, target: Target) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
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
            engine=self.name,
            success=True,
            findings=[finding],
            raw_output="",
            artifacts={},
            started_at=started,
            completed_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_staged_dispatch_katana_then_nuclei():
    scan_job_id = uuid.uuid4()
    target = Target(
        scan_job_id=scan_job_id,
        target_url="https://example.com",
        hostname="example.com",
        options={},
    )

    results = await staged_dispatch(target, ["mock_katana", "mock_nuclei"])

    assert len(results) == 2
    katana_res = next(r for r in results if r.engine == "mock_katana")
    nuclei_res = next(r for r in results if r.engine == "mock_nuclei")

    assert katana_res.success is True
    assert nuclei_res.success is True

    urls_file = katana_res.artifacts.get("urls_file")
    assert urls_file is not None

    # Verify that the forwarded temp file is cleaned up after the run.
    assert not os.path.exists(urls_file)
