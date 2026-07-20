"""SSL/TLS engine tests.

Uses a locally-generated self-signed certificate served by a throwaway stdlib
TLS server on 127.0.0.1 — no external services, no network dependency, fully
deterministic. Requires the `openssl` CLI (present in the dev/CI toolchain) to
mint the test certs; tests skip cleanly if it isn't available.
"""

import shutil
import socket
import ssl
import subprocess
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from appsec.scanner.engines.ssl_tls_engine import SslTlsScanner
from appsec.scanner.interfaces.models import Severity, Target

requires_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl CLI not available")


def _make_self_signed(tmp: Path, days: int) -> tuple[Path, Path]:
    """Generate a self-signed cert/key for CN=localhost. Positive `days` => valid
    for that many days; `days <= 0` => a cert that has already expired."""
    key = tmp / "key.pem"
    cert = tmp / "cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=localhost",
            "-days",
            str(days),
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


class _TLSServer:
    """Minimal threaded TLS server that presents the given cert to one client."""

    def __init__(self, cert: Path, key: Path) -> None:
        self._ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self._ctx.load_cert_chain(certfile=str(cert), keyfile=str(key))
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(5)
        self.port = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def _serve(self) -> None:
        self._sock.settimeout(0.5)
        while not self._stop.is_set():
            try:
                client, _ = self._sock.accept()
            except (TimeoutError, OSError):
                continue
            try:
                with self._ctx.wrap_socket(client, server_side=True) as tls:
                    tls.recv(1024)
            except OSError:
                pass

    def __enter__(self) -> "_TLSServer":
        self._thread.start()
        return self

    def __exit__(self, *args) -> None:
        self._stop.set()
        self._sock.close()
        self._thread.join(timeout=2)


@pytest.fixture
def tmp_certs(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path


def _target(port: int, hostname: str = "localhost") -> Target:
    return Target(
        hostname=hostname,
        scan_job_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        options={"port": port},
    )


def _titles(result) -> set[str]:
    return {f.title for f in result.findings}


@pytest.mark.asyncio
@requires_openssl
async def test_self_signed_flagged_high(tmp_certs: Path) -> None:
    cert, key = _make_self_signed(tmp_certs, days=365)
    with _TLSServer(cert, key) as server:
        result = await SslTlsScanner().scan(_target(server.port))
    assert result.success
    self_signed = [f for f in result.findings if f.title == "Self-signed certificate"]
    assert self_signed and self_signed[0].severity is Severity.HIGH
    # Summary is always emitted.
    assert "TLS certificate summary" in _titles(result)


def _cert_time(delta_days: int) -> str:
    """A notAfter string in getpeercert()'s format, offset from now."""
    from datetime import UTC, datetime, timedelta

    when = datetime.now(UTC) + timedelta(days=delta_days)
    return when.strftime("%b %d %H:%M:%S %Y GMT")


@pytest.mark.parametrize(
    ("delta_days", "expected_title", "expected_severity"),
    [
        (-1, "TLS certificate expired", Severity.CRITICAL),
        (3, "TLS certificate expiring soon", Severity.HIGH),  # within 7 days
        (20, "TLS certificate expiring soon", Severity.MEDIUM),  # within 30 days
    ],
)
def test_expiry_thresholds(delta_days, expected_title, expected_severity) -> None:
    # Directly exercises the expiry-severity logic without needing a backdated
    # cert (the local OpenSSL build can't mint one).
    findings = SslTlsScanner()._check_expiry("example.com", _cert_time(delta_days))
    assert findings and findings[0].title == expected_title
    assert findings[0].severity is expected_severity


def test_expiry_far_future_no_finding() -> None:
    assert SslTlsScanner()._check_expiry("example.com", _cert_time(200)) == []


@pytest.mark.asyncio
@requires_openssl
async def test_hostname_mismatch_flagged_high(tmp_certs: Path) -> None:
    # Cert CN is "localhost"; connect claiming a different hostname.
    # Cert CN is "localhost"; connect via 127.0.0.1 (resolves locally, but the
    # cert does not cover that name) to trigger a mismatch.
    cert, key = _make_self_signed(tmp_certs, days=365)
    with _TLSServer(cert, key) as server:
        result = await SslTlsScanner().scan(_target(server.port, hostname="127.0.0.1"))
    assert result.success
    mismatch = [f for f in result.findings if f.title == "Certificate hostname mismatch"]
    assert mismatch and mismatch[0].severity is Severity.HIGH


@pytest.mark.asyncio
@requires_openssl
async def test_connection_failure_returns_unsuccessful_result() -> None:
    # Nothing listening on this port.
    result = await SslTlsScanner().scan(_target(1))
    assert not result.success
    assert result.error_message
