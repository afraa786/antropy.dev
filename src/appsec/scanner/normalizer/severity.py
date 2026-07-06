"""Maps arbitrary engine-reported severity strings onto our canonical
`Severity` enum. Each engine adapter owns its own raw vocabulary (Nuclei's
"critical/high/medium/low/info/unknown", TruffleHog's verified/unverified,
etc.) — this module only defines the common target enum + a generic
best-effort mapper for free-text input the orchestrator/normalizer can use
before an adapter's own mapping is available.
"""

from appsec.scanner.interfaces.models import Severity

_ALIASES: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "moderate": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "informational": Severity.INFO,
    "unknown": Severity.INFO,
}


def normalize_severity(raw: str | None) -> Severity:
    """Best-effort mapping from a free-text severity label to `Severity`.
    Unknown/missing input defaults to INFO rather than raising — severity
    normalization must never block ingestion of a finding.
    """
    if raw is None:
        return Severity.INFO
    return _ALIASES.get(raw.strip().lower(), Severity.INFO)
