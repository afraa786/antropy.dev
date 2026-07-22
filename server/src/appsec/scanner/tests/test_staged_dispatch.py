"""Staged dispatcher: proves one stage's artifacts feed the next stage's
Target.options (the katana -> nuclei handoff), and that forwarded temp files
are cleaned up after the run.
"""

import os
import tempfile
import uuid

import pytest

from appsec.scanner.interfaces.models import ScanResult, Target
from appsec.scanner.interfaces.registry import clear_registry, register_scanner
from appsec.scanner.interfaces.scanner import Scanner
from appsec.scanner.orchestrator.dispatcher import dispatch_staged


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_registry()
    yield
    clear_registry()


def _make_target(**options) -> Target:
    return Target(
        hostname="example.com",
        scan_job_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        options=options,
    )


@pytest.mark.asyncio
async def test_artifact_from_stage_one_reaches_stage_two_options() -> None:
    # A crawler publishes a urls_file artifact; a downstream engine records what
    # it received in its Target.options.
    fd, urls_path = tempfile.mkstemp(prefix="test_urls_", suffix=".txt")
    with os.fdopen(fd, "w") as fh:
        fh.write("https://example.com/a\nhttps://example.com/b")

    received: dict = {}

    @register_scanner
    class FakeCrawler(Scanner):
        name = "fake_crawler"
        category = None  # not used; we drive stages explicitly

        async def validate(self, target):
            return True

        async def health_check(self):
            return True

        async def scan(self, target):
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=True,
                artifacts={"urls_file": urls_path},
            )

    @register_scanner
    class FakeVuln(Scanner):
        name = "fake_vuln"
        category = None

        async def validate(self, target):
            return True

        async def health_check(self):
            return True

        async def scan(self, target):
            # Capture the option the dispatcher injected from the crawler's artifact.
            received["nuclei_url_list"] = target.options.get("nuclei_url_list")
            return ScanResult(scan_job_id=target.scan_job_id, engine=self.name, success=True)

    target = _make_target()
    results = await dispatch_staged([["fake_crawler"], ["fake_vuln"]], target)

    # The vuln engine saw the crawler's file path in its options.
    assert received["nuclei_url_list"] == urls_path
    assert {r.engine for r in results} == {"fake_crawler", "fake_vuln"}
    assert all(r.success for r in results)

    # The forwarded temp file is cleaned up by the dispatcher after the run.
    assert not os.path.exists(urls_path)


@pytest.mark.asyncio
async def test_stage_one_options_are_not_leaked_backwards() -> None:
    # The caller's original Target.options must not be mutated by staging.
    @register_scanner
    class NoopEngine(Scanner):
        name = "noop"
        category = None

        async def validate(self, target):
            return True

        async def health_check(self):
            return True

        async def scan(self, target):
            return ScanResult(scan_job_id=target.scan_job_id, engine=self.name, success=True)

    target = _make_target(existing="value")
    await dispatch_staged([["noop"]], target)

    assert target.options == {"existing": "value"}
