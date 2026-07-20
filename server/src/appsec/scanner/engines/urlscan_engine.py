"""urlscan.io engine adapter.

Two-phase engine: submit a scan, then poll for the result (urlscan runs the
scan asynchronously on their side). Because a result can take up to ~2 minutes,
this engine is intended to run as its own Celery task (see
`infrastructure.tasks.urlscan_execution`) so it never blocks the fast engines
from completing the scan job — its findings are appended progressively.

Output matches the common Finding/ScanResult schema every adapter produces.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from appsec.config import get_settings
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

_SUBMIT_URL = "https://urlscan.io/api/v1/scan/"
_RESULT_URL = "https://urlscan.io/api/v1/result/{uuid}/"
_POLL_INTERVAL_SECONDS = 10
_POLL_MAX_ATTEMPTS = 12
_SECURITY_HEADERS = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
]


class UrlscanConfigError(RuntimeError):
    """Raised at registration time when URLSCAN_API_KEY is not configured."""


def _new_finding(
    title: str,
    severity: Severity,
    description: str,
    *,
    matched_at: str | None = None,
    evidence: list[Evidence] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    import uuid

    return Finding(
        id=uuid.uuid4(),
        title=title,
        severity=severity,
        description=description,
        engine=UrlscanScanner.name,
        matched_at=matched_at,
        evidence=evidence or [],
        tags=tags or [],
        metadata=metadata or {},
    )


@register_scanner
class UrlscanScanner(Scanner):
    name = "urlscan"
    category = ScanEngineCategory.HTTP_PROBE

    def __init__(self) -> None:
        self._api_key = get_settings().urlscan_api_key
        # Fail loud and early — never bury a missing key inside a scan run.
        if not self._api_key:
            raise UrlscanConfigError(
                "URLSCAN_API_KEY is not set — the urlscan engine cannot run. "
                "Set it in the environment (.env) before enabling this engine."
            )

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        url = f"https://{target.hostname}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                scan_uuid = await self._submit(client, url)
                result_json = await self._poll(client, scan_uuid)
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("urlscan_failed", hostname=target.hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=str(exc),
                started_at=started,
                completed_at=datetime.now(UTC),
            )

        if result_json is None:
            findings = [
                _new_finding(
                    "urlscan.io scan did not complete in time",
                    Severity.INFO,
                    f"urlscan.io did not return a result for {url} within "
                    f"~{_POLL_INTERVAL_SECONDS * _POLL_MAX_ATTEMPTS}s. The scan may still "
                    "be processing on urlscan's side.",
                    matched_at=url,
                    tags=["urlscan", "timeout"],
                )
            ]
        else:
            findings = self._parse(result_json, url)

        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=self.name,
            findings=findings,
            success=True,
            started_at=started,
            completed_at=datetime.now(UTC),
        )

    async def _submit(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.post(
            _SUBMIT_URL,
            headers={"Content-Type": "application/json", "api-key": self._api_key},
            json={"url": url, "visibility": "unlisted", "tags": ["entropy-scan"]},
        )
        response.raise_for_status()
        return response.json()["uuid"]

    async def _poll(self, client: httpx.AsyncClient, scan_uuid: str) -> dict[str, Any] | None:
        result_url = _RESULT_URL.format(uuid=scan_uuid)
        for attempt in range(_POLL_MAX_ATTEMPTS):
            response = await client.get(result_url, headers={"api-key": self._api_key})
            if response.status_code == 200:
                return response.json()
            if response.status_code != 404:
                response.raise_for_status()
            # 404 => still processing; wait and retry (skip sleep on last attempt)
            if attempt < _POLL_MAX_ATTEMPTS - 1:
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        return None

    def _parse(self, result: dict[str, Any], url: str) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._parse_verdict(result, url))
        findings.extend(self._parse_security_headers(result, url))
        findings.extend(self._parse_technologies(result, url))
        findings.extend(self._parse_tls(result, url))
        findings.extend(self._parse_domain_age(result, url))
        findings.extend(self._parse_screenshot(result, url))
        findings.extend(self._parse_redirects(result, url))
        return findings

    def _parse_verdict(self, result: dict[str, Any], url: str) -> list[Finding]:
        overall = result.get("verdicts", {}).get("overall", {})
        if overall.get("malicious"):
            score = overall.get("score")
            return [
                _new_finding(
                    "Malicious verdict from urlscan.io",
                    Severity.CRITICAL,
                    f"urlscan.io flagged {url} as malicious (score: {score}).",
                    matched_at=url,
                    tags=["urlscan", "malicious"],
                    metadata={"score": score, "categories": overall.get("categories", [])},
                )
            ]
        return []

    def _parse_security_headers(self, result: dict[str, Any], url: str) -> list[Finding]:
        requests = result.get("data", {}).get("requests", [])
        if not requests:
            return []
        headers = requests[0].get("response", {}).get("response", {}).get("securityHeaders", [])
        present = {h.get("name", "").lower() for h in headers}
        missing = [h for h in _SECURITY_HEADERS if h.lower() not in present]
        if not missing:
            return []
        return [
            _new_finding(
                "Missing security headers",
                Severity.MEDIUM,
                f"The primary document response is missing: {', '.join(missing)}.",
                matched_at=url,
                tags=["urlscan", "headers"],
                metadata={"missing": missing},
            )
        ]

    def _parse_technologies(self, result: dict[str, Any], url: str) -> list[Finding]:
        apps = result.get("meta", {}).get("processors", {}).get("wappa", {}).get("data", [])
        names = [a.get("app") for a in apps if a.get("app")]
        if not names:
            return []
        return [
            _new_finding(
                "Detected technologies",
                Severity.INFO,
                f"Technologies detected on {url}: {', '.join(names)}.",
                matched_at=url,
                tags=["urlscan", "tech"],
                metadata={"technologies": names},
            )
        ]

    def _parse_tls(self, result: dict[str, Any], url: str) -> list[Finding]:
        page = result.get("page", {})
        valid_days = page.get("tlsValidDays")
        issuer = page.get("tlsIssuer")
        certs = result.get("lists", {}).get("certificates", [])
        cert = certs[0] if certs else {}
        metadata = {
            "issuer": issuer,
            "tlsValidDays": valid_days,
            "tlsAgeDays": page.get("tlsAgeDays"),
            "certificate": cert,
        }
        if isinstance(valid_days, int) and valid_days < 30:
            return [
                _new_finding(
                    "TLS certificate expiring soon",
                    Severity.MEDIUM,
                    f"The TLS certificate for {url} is valid for only {valid_days} more day(s) "
                    f"(issuer: {issuer}).",
                    matched_at=url,
                    tags=["urlscan", "tls"],
                    metadata=metadata,
                )
            ]
        return [
            _new_finding(
                "TLS certificate summary",
                Severity.INFO,
                f"TLS certificate for {url} issued by {issuer}, valid for {valid_days} more day(s).",
                matched_at=url,
                tags=["urlscan", "tls"],
                metadata=metadata,
            )
        ]

    def _parse_domain_age(self, result: dict[str, Any], url: str) -> list[Finding]:
        age = result.get("page", {}).get("apexDomainAgeDays")
        if age is None:
            return []
        return [
            _new_finding(
                "Domain age",
                Severity.INFO,
                f"The apex domain for {url} is approximately {age} day(s) old.",
                matched_at=url,
                tags=["urlscan", "domain-age"],
                metadata={"apexDomainAgeDays": age},
            )
        ]

    def _parse_screenshot(self, result: dict[str, Any], url: str) -> list[Finding]:
        screenshot = result.get("task", {}).get("screenshotURL")
        if not screenshot:
            return []
        return [
            _new_finding(
                "Page screenshot captured",
                Severity.INFO,
                f"urlscan.io captured a screenshot of {url}.",
                matched_at=url,
                evidence=[
                    Evidence(
                        description="Screenshot URL",
                        raw_data=screenshot,
                        metadata={"type": "screenshot"},
                    )
                ],
                tags=["urlscan", "screenshot"],
                metadata={"screenshotURL": screenshot},
            )
        ]

    def _parse_redirects(self, result: dict[str, Any], url: str) -> list[Finding]:
        redirects = result.get("data", {}).get("redirects", [])
        if len(redirects) <= 1:
            return []
        # More than a single hop — surface the chain as low-severity context.
        chain = [r.get("url") for r in redirects if r.get("url")]
        domains = {httpx.URL(u).host for u in chain if u}
        if len(domains) <= 1:
            return []
        return [
            _new_finding(
                "Multi-domain redirect chain",
                Severity.LOW,
                f"{url} redirects through multiple domains: {', '.join(sorted(domains))}.",
                matched_at=url,
                tags=["urlscan", "redirects"],
                metadata={"chain": chain},
            )
        ]
