"""Placeholder for AI-generated natural-language scan summaries. No LLM
integration exists yet — this stub defines the seam so a future
implementation (calling out to Claude/another model) only needs to fill in
`generate_summary()` without the caller (report service) changing.
"""

from typing import Any

from appsec.scanner.orchestrator.pipeline import PipelineOutput


async def generate_summary(output: PipelineOutput) -> str | None:
    """Returns a human-readable summary of scan findings, or None if AI
    summarization isn't configured/implemented yet. Callers must treat
    `None` as "no summary available", not an error.
    """
    return None


def summary_context(output: PipelineOutput) -> dict[str, Any]:
    """Structured context a future AI summarizer would consume — separated
    from `generate_summary` so the prompt-building input is testable without
    any model call.
    """
    return {
        "total_findings": len(output.findings),
        "severity_counts": output.severity_counts,
        "failed_engines": output.failed_engines,
        "top_findings": [
            {"title": f.title, "severity": f.severity.value} for f in output.findings[:10]
        ],
    }
