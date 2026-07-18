import uuid

import pytest

from appsec.scanner.interfaces.registry import clear_registry
from appsec.scanner.orchestrator.orchestrator import run_scan


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.mark.asyncio
async def test_run_scan_with_no_registered_engines_returns_empty_output() -> None:
    output = await run_scan(
        scan_job_id=uuid.uuid4(), organization_id=uuid.uuid4(), hostname="example.com"
    )
    assert output.findings == []
    assert output.failed_engines == []
