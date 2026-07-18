"""urlscan.io engine tests with fully mocked HTTP — never hits the real API.

Covers: successful submit+poll+parse, a 404-then-200 polling sequence, and the
poll-timeout case.
"""

import uuid
from unittest.mock import patch

import pytest

from appsec.scanner.interfaces.models import Severity, Target


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    # Engine __init__ requires a key; get_settings is cached so patch the env
    # and clear the cache.
    from appsec.config import get_settings

    monkeypatch.setenv("URLSCAN_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _target() -> Target:
    return Target(
        hostname="example.com", scan_job_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )


# A trimmed but structurally-real urlscan result (paths match the parser).
_RESULT_JSON = {
    "verdicts": {"overall": {"malicious": True, "score": 80, "categories": ["phishing"]}},
    "data": {
        "requests": [
            {
                "response": {
                    "response": {
                        "securityHeaders": [
                            {"name": "X-Frame-Options", "value": "DENY"},
                        ]
                    }
                }
            }
        ],
        "redirects": [
            {"url": "http://example.com/"},
            {"url": "https://evil.example.net/"},
        ],
    },
    "meta": {
        "processors": {
            "wappa": {"data": [{"app": "WordPress"}, {"app": "Google Analytics"}]}
        }
    },
    "page": {
        "tlsIssuer": "Let's Encrypt",
        "tlsValidDays": 12,
        "tlsAgeDays": 3,
        "apexDomainAgeDays": 400,
    },
    "lists": {"certificates": [{"subjectName": "example.com"}]},
    "task": {"screenshotURL": "https://urlscan.io/screenshots/abc.png"},
}


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("error", request=None, response=None)


class _FakeClient:
    """Scripts POST (submit) then a sequence of GET (poll) responses."""

    def __init__(self, submit: _FakeResponse, polls: list[_FakeResponse]) -> None:
        self._submit = submit
        self._polls = polls
        self._poll_idx = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs) -> _FakeResponse:
        return self._submit

    async def get(self, *args, **kwargs) -> _FakeResponse:
        resp = self._polls[min(self._poll_idx, len(self._polls) - 1)]
        self._poll_idx += 1
        return resp


def _run_with_client(fake_client):
    import asyncio

    from appsec.scanner.engines.urlscan_engine import UrlscanScanner

    async def _run():
        with patch("httpx.AsyncClient", return_value=fake_client), patch(
            "appsec.scanner.engines.urlscan_engine.asyncio.sleep", return_value=None
        ):
            return await UrlscanScanner().scan(_target())

    return asyncio.run(_run())


def _titles(result) -> set[str]:
    return {f.title for f in result.findings}


def test_submit_poll_parse_success() -> None:
    submit = _FakeResponse(200, {"uuid": "abc-123"})
    poll = _FakeResponse(200, _RESULT_JSON)
    result = _run_with_client(_FakeClient(submit, [poll]))

    assert result.success
    titles = _titles(result)
    assert "Malicious verdict from urlscan.io" in titles
    assert "Missing security headers" in titles
    assert "Detected technologies" in titles
    assert "TLS certificate expiring soon" in titles  # tlsValidDays=12 < 30
    assert "Domain age" in titles
    assert "Page screenshot captured" in titles
    assert "Multi-domain redirect chain" in titles

    malicious = next(f for f in result.findings if f.title.startswith("Malicious"))
    assert malicious.severity is Severity.CRITICAL


def test_poll_404_then_200() -> None:
    submit = _FakeResponse(200, {"uuid": "abc-123"})
    polls = [_FakeResponse(404), _FakeResponse(404), _FakeResponse(200, _RESULT_JSON)]
    result = _run_with_client(_FakeClient(submit, polls))

    assert result.success
    assert "Malicious verdict from urlscan.io" in _titles(result)


def test_poll_timeout_returns_informational_finding() -> None:
    submit = _FakeResponse(200, {"uuid": "abc-123"})
    # Always 404 -> never completes -> single informational timeout finding.
    result = _run_with_client(_FakeClient(submit, [_FakeResponse(404)]))

    assert result.success
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity is Severity.INFO
    assert "did not complete" in finding.title
