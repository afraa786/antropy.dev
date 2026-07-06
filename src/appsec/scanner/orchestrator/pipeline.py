"""Turns raw per-engine `ScanResult`s into the normalized, deduplicated,
severity-sorted finding set stored against a scan job. Sits between the
dispatcher (execution) and the orchestrator (public API) so normalization
rules can change without touching either.
"""

from appsec.scanner.interfaces.models import Finding, ScanResult
from appsec.scanner.normalizer.findings import deduplicate, severity_counts, sort_by_severity


class PipelineOutput:
    __slots__ = ("findings", "severity_counts", "failed_engines")

    def __init__(
        self, findings: list[Finding], counts: dict[str, int], failed_engines: list[str]
    ) -> None:
        self.findings = findings
        self.severity_counts = counts
        self.failed_engines = failed_engines


def process(results: list[ScanResult]) -> PipelineOutput:
    """Merges findings from every successful engine result, deduplicates,
    and sorts by severity. Failed engines are reported separately rather
    than silently dropped.
    """
    all_findings: list[Finding] = []
    failed_engines: list[str] = []

    for result in results:
        if not result.success:
            failed_engines.append(result.engine)
            continue
        all_findings.extend(result.findings)

    findings = sort_by_severity(deduplicate(all_findings))
    return PipelineOutput(findings, severity_counts(findings), failed_engines)
