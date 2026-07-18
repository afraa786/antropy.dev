"""Turns a `PipelineOutput` (normalized findings) into plain serializable
dicts for report generation. No rendering (PDF/HTML) here — that's the
exporter's job; this module only shapes the data.
"""

from typing import Any

from appsec.scanner.interfaces.models import Finding
from appsec.scanner.orchestrator.pipeline import PipelineOutput


def finding_to_dict(finding: Finding) -> dict[str, Any]:
    return {
        "id": str(finding.id),
        "title": finding.title,
        "severity": finding.severity.value,
        "description": finding.description,
        "engine": finding.engine,
        "matched_at": finding.matched_at,
        "tags": finding.tags,
        "evidence": [
            {"description": e.description, "raw_data": e.raw_data, "metadata": e.metadata}
            for e in finding.evidence
        ],
        "metadata": finding.metadata,
    }


def format_report(output: PipelineOutput) -> dict[str, Any]:
    return {
        "summary": {
            "total_findings": len(output.findings),
            "severity_counts": output.severity_counts,
            "failed_engines": output.failed_engines,
        },
        "findings": [finding_to_dict(f) for f in output.findings],
    }
