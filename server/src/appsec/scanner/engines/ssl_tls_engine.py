"""SSL/TLS certificate checker engine — stdlib only (ssl + socket), no external
dependencies. Connects to the target on port 443, inspects the negotiated
certificate/protocol/cipher, and emits normalized findings.

Output matches the common Finding/ScanResult schema every adapter produces.
"""

import socket
import ssl
import uuid
from datetime import UTC, datetime
from typing import Any

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

_PORT = 443
_CONNECT_TIMEOUT = 10.0
_DEPRECATED_PROTOCOLS = {"TLSv1", "TLSv1.0", "TLSv1.1"}
_WEAK_CIPHER_TOKENS = ("RC4", "DES", "NULL", "EXPORT")
_CERT_TIME_FORMAT = "%b %d %H:%M:%S %Y %Z"


def _new_finding(
    title: str,
    severity: Severity,
    description: str,
    *,
    matched_at: str,
    evidence: list[Evidence] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        title=title,
        severity=severity,
        description=description,
        engine=SslTlsScanner.name,
        matched_at=matched_at,
        evidence=evidence or [],
        tags=tags or ["ssl", "tls"],
        metadata=metadata or {},
    )


def _rdn_to_dict(rdn_sequence: Any) -> dict[str, str]:
    """Flatten getpeercert()'s nested subject/issuer tuple sequence to a dict."""
    out: dict[str, str] = {}
    for rdn in rdn_sequence or ():
        for key, value in rdn:
            out[key] = value
    return out


def _san_hostnames(cert: dict[str, Any]) -> list[str]:
    return [value for key, value in cert.get("subjectAltName", ()) if key == "DNS"]


def _hostname_matches(hostname: str, cn: str | None, sans: list[str]) -> bool:
    candidates = list(sans)
    if cn:
        candidates.append(cn)
    for candidate in candidates:
        if candidate == hostname:
            return True
        if candidate.startswith("*."):
            suffix = candidate[1:]  # ".example.com"
            if hostname.endswith(suffix) and hostname.count(".") == candidate.count("."):
                return True
    return False


@register_scanner
class SslTlsScanner(Scanner):
    name = "ssl_tls"
    category = ScanEngineCategory.VULNERABILITY_SCAN

    async def validate(self, target: Target) -> bool:
        return bool(target.hostname)

    async def health_check(self) -> bool:
        return True  # stdlib only — always available

    async def scan(self, target: Target) -> ScanResult:
        started = datetime.now(UTC)
        hostname = target.hostname
        port = int(target.options.get("port", _PORT))
        try:
            cert, protocol, cipher = self._fetch_cert(hostname, port)
        except Exception as exc:  # noqa: BLE001 -- surface as engine-level failure
            logger.error("ssl_tls_connect_failed", hostname=hostname, error=str(exc))
            return ScanResult(
                scan_job_id=target.scan_job_id,
                engine=self.name,
                success=False,
                error_message=f"TLS connection to {hostname}:{port} failed: {exc}",
                started_at=started,
                completed_at=datetime.now(UTC),
            )

        findings = self._analyze(hostname, cert, protocol, cipher)
        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=self.name,
            findings=findings,
            success=True,
            started_at=started,
            completed_at=datetime.now(UTC),
        )

    def _fetch_cert(
        self, hostname: str, port: int
    ) -> tuple[dict[str, Any], str | None, tuple | None]:
        """Return (peer cert dict, negotiated protocol, cipher tuple). Uses a
        verifying context first; on verify failure (expired/self-signed/mismatch)
        retries without verification so we can still inspect the presented cert.
        """
        context = ssl.create_default_context()
        try:
            return self._connect(context, hostname, port)
        except ssl.SSLError:
            # Re-fetch the cert without verification so we can report *why* it
            # failed (expired, self-signed, hostname mismatch) as findings.
            insecure = ssl.create_default_context()
            insecure.check_hostname = False
            insecure.verify_mode = ssl.CERT_NONE
            return self._connect(insecure, hostname, port)

    def _connect(
        self, context: ssl.SSLContext, hostname: str, port: int
    ) -> tuple[dict[str, Any], str | None, tuple | None]:
        with socket.create_connection(
            (hostname, port), timeout=_CONNECT_TIMEOUT
        ) as sock, context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            # getpeercert() returns {} when verification is disabled; fall back
            # to decoding the DER form into the same dict structure.
            if not cert:
                cert = self._decode_der(ssock.getpeercert(binary_form=True))
            return cert, ssock.version(), ssock.cipher()

    @staticmethod
    def _decode_der(der: bytes | None) -> dict[str, Any]:
        if not der:
            return {}
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as tmp:
            tmp.write(ssl.DER_cert_to_PEM_cert(der))
            path = tmp.name
        try:
            return ssl._ssl._test_decode_cert(path)  # type: ignore[attr-defined]
        finally:
            import os

            os.unlink(path)

    def _analyze(
        self, hostname: str, cert: dict[str, Any], protocol: str | None, cipher: tuple | None
    ) -> list[Finding]:
        findings: list[Finding] = []
        subject = _rdn_to_dict(cert.get("subject"))
        issuer = _rdn_to_dict(cert.get("issuer"))
        sans = _san_hostnames(cert)
        cn = subject.get("commonName")
        cipher_name = cipher[0] if cipher else None
        not_after = cert.get("notAfter")

        findings.extend(self._check_expiry(hostname, not_after))
        findings.extend(self._check_hostname(hostname, cn, sans))
        findings.extend(self._check_self_signed(hostname, subject, issuer))
        findings.extend(self._check_protocol(hostname, protocol))
        findings.extend(self._check_cipher(hostname, cipher_name))

        # Always emit a summary finding — useful AI-summary context even when clean.
        findings.append(
            _new_finding(
                "TLS certificate summary",
                Severity.INFO,
                f"{hostname}: issuer={issuer.get('organizationName') or issuer.get('commonName')}, "
                f"valid until {not_after}, protocol={protocol}, cipher={cipher_name}.",
                matched_at=hostname,
                metadata={
                    "issuer": issuer,
                    "subject": subject,
                    "san": sans,
                    "not_after": not_after,
                    "protocol": protocol,
                    "cipher": cipher_name,
                },
            )
        )
        return findings

    def _check_expiry(self, hostname: str, not_after: str | None) -> list[Finding]:
        if not not_after:
            return []
        try:
            expires = datetime.strptime(not_after, _CERT_TIME_FORMAT).replace(tzinfo=UTC)
        except ValueError:
            return []
        days_left = (expires - datetime.now(UTC)).days
        evidence = [Evidence(description="notAfter", raw_data=not_after)]
        if days_left < 0:
            return [
                _new_finding(
                    "TLS certificate expired",
                    Severity.CRITICAL,
                    f"The certificate for {hostname} expired {-days_left} day(s) ago ({not_after}).",
                    matched_at=hostname,
                    evidence=evidence,
                    metadata={"days_left": days_left},
                )
            ]
        if days_left <= 7:
            severity = Severity.HIGH
        elif days_left <= 30:
            severity = Severity.MEDIUM
        else:
            return []
        return [
            _new_finding(
                "TLS certificate expiring soon",
                severity,
                f"The certificate for {hostname} expires in {days_left} day(s) ({not_after}).",
                matched_at=hostname,
                evidence=evidence,
                metadata={"days_left": days_left},
            )
        ]

    def _check_hostname(self, hostname: str, cn: str | None, sans: list[str]) -> list[Finding]:
        if _hostname_matches(hostname, cn, sans):
            return []
        return [
            _new_finding(
                "Certificate hostname mismatch",
                Severity.HIGH,
                f"{hostname} is not covered by the certificate's CN ({cn}) or SANs ({sans}).",
                matched_at=hostname,
                metadata={"cn": cn, "san": sans},
            )
        ]

    def _check_self_signed(
        self, hostname: str, subject: dict[str, str], issuer: dict[str, str]
    ) -> list[Finding]:
        if subject and issuer and subject == issuer:
            return [
                _new_finding(
                    "Self-signed certificate",
                    Severity.HIGH,
                    f"The certificate for {hostname} is self-signed (issuer equals subject).",
                    matched_at=hostname,
                    metadata={"subject": subject, "issuer": issuer},
                )
            ]
        return []

    def _check_protocol(self, hostname: str, protocol: str | None) -> list[Finding]:
        if protocol in _DEPRECATED_PROTOCOLS:
            return [
                _new_finding(
                    "Deprecated TLS protocol",
                    Severity.MEDIUM,
                    f"{hostname} negotiated {protocol}, which is deprecated and insecure.",
                    matched_at=hostname,
                    metadata={"protocol": protocol},
                )
            ]
        return []

    def _check_cipher(self, hostname: str, cipher_name: str | None) -> list[Finding]:
        if cipher_name and any(token in cipher_name.upper() for token in _WEAK_CIPHER_TOKENS):
            return [
                _new_finding(
                    "Weak cipher suite",
                    Severity.HIGH,
                    f"{hostname} negotiated a weak cipher suite: {cipher_name}.",
                    matched_at=hostname,
                    metadata={"cipher": cipher_name},
                )
            ]
        return []
