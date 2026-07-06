"""Aggregation utilities applied to already-normalized `Finding` lists — this
module never touches raw engine output, only the common DTOs every adapter
must already produce.
"""

from appsec.scanner.interfaces.models import Finding, Severity


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    """Tally findings per severity level, always including every severity
    key (zero-filled) so downstream consumers (API responses, reports) get a
    stable shape regardless of what was actually found.
    """
    counts = {severity.value: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity.value] += 1
    return counts


def deduplicate(findings: list[Finding]) -> list[Finding]:
    """Drops findings that are exact duplicates across engines — same
    title + matched_at + engine combination. Cross-engine duplicates with
    differing engines are preserved since corroboration from multiple tools
    is useful signal, not noise.
    """
    seen: set[tuple[str, str | None, str]] = set()
    deduped: list[Finding] = []
    for finding in findings:
        key = (finding.title, finding.matched_at, finding.engine)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def sort_by_severity(findings: list[Finding]) -> list[Finding]:
    order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }
    return sorted(findings, key=lambda f: order[f.severity])
