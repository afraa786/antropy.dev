import uuid

import pytest

from appsec.scanner.interfaces.models import ScanEngineCategory, ScanResult, Target
from appsec.scanner.interfaces.registry import (
    ScannerAlreadyRegisteredError,
    ScannerNotFoundError,
    clear_registry,
    get_scanner,
    list_scanners,
    register_scanner,
)
from appsec.scanner.interfaces.scanner import Scanner


class _StubScanner(Scanner):
    name = "stub"
    category = ScanEngineCategory.HTTP_PROBE

    async def validate(self, target: Target) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def scan(self, target: Target) -> ScanResult:
        return ScanResult(scan_job_id=target.scan_job_id, engine=self.name)


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_registry()
    yield
    clear_registry()


def test_register_and_lookup_scanner() -> None:
    register_scanner(_StubScanner)
    assert get_scanner("stub") is _StubScanner
    assert "stub" in list_scanners()


def test_duplicate_registration_raises() -> None:
    register_scanner(_StubScanner)
    with pytest.raises(ScannerAlreadyRegisteredError):
        register_scanner(_StubScanner)


def test_unknown_scanner_raises() -> None:
    with pytest.raises(ScannerNotFoundError):
        get_scanner("does-not-exist")


@pytest.mark.asyncio
async def test_stub_scanner_runs() -> None:
    register_scanner(_StubScanner)
    scanner = _StubScanner()
    target = Target(hostname="example.com", scan_job_id=uuid.uuid4(), organization_id=uuid.uuid4())
    result = await scanner.scan(target)
    assert result.success
    assert result.engine == "stub"
