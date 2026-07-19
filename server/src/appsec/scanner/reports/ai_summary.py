"""AI-generated natural-language scan summaries via OpenRouter.

`generate_summary()` calls an OpenRouter chat model (OpenAI-compatible API)
to turn normalized scan findings into a short human-readable summary. If the
API key is missing or the call fails for any reason, it falls back to a
deterministic severity-based summary rather than raising — an AI outage must
never fail a scan.
"""

from typing import Any

import httpx

from appsec.config import get_settings
from appsec.logging import get_logger
from appsec.scanner.orchestrator.pipeline import PipelineOutput

logger = get_logger(__name__)


def summary_context(output: PipelineOutput) -> dict[str, Any]:
    """Structured context the AI summarizer consumes — separated from
    `generate_summary` so the prompt-building input is testable without any
    model call.
    """
    return {
        "total_findings": len(output.findings),
        "severity_counts": output.severity_counts,
        "failed_engines": output.failed_engines,
        "top_findings": [{"title": f.title, "severity": f.severity.value} for f in output.findings[:10]],
    }


def _fallback_summary(context: dict[str, Any]) -> str:
    """Deterministic, no-AI summary built from severity counts. Used whenever
    the OpenRouter call is unavailable or fails.
    """
    total = context["total_findings"]
    if total == 0:
        return "Scan completed with no findings."

    counts = context["severity_counts"]
    parts = [f"{count} {sev}" for sev, count in counts.items() if count]
    breakdown = ", ".join(parts) if parts else "no severity breakdown available"
    summary = f"Scan completed with {total} finding(s): {breakdown}."

    failed = context.get("failed_engines") or []
    if failed:
        summary += f" Note: {len(failed)} engine(s) failed to run ({', '.join(failed)})."
    return summary


def _build_prompt(context: dict[str, Any]) -> str:
    lines = [
        "You are a security analyst. Write a concise (2-4 sentence) executive summary "
        "of the following application security scan results. Focus on risk and what to "
        "prioritize. Do not invent findings beyond those listed.",
        "",
        f"Total findings: {context['total_findings']}",
        f"Severity counts: {context['severity_counts']}",
    ]
    if context.get("failed_engines"):
        lines.append(f"Engines that failed to run: {context['failed_engines']}")
    if context.get("top_findings"):
        lines.append("Top findings:")
        for f in context["top_findings"]:
            lines.append(f"  - [{f['severity']}] {f['title']}")
    return "\n".join(lines)


async def generate_summary(output: PipelineOutput) -> str:
    """Returns a human-readable summary of scan findings. Never returns None
    and never raises: on any failure it falls back to a deterministic
    severity-based summary so the scan pipeline is unaffected.
    """
    context = summary_context(output)
    settings = get_settings()

    if not settings.openrouter_api_key:
        logger.info("ai_summary_no_key_using_fallback")
        return _fallback_summary(context)

    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [
                        {"role": "user", "content": _build_prompt(context)},
                    ],
                    "max_tokens": 300,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if not content:
                raise ValueError("empty completion")
            logger.info("ai_summary_generated", model=settings.openrouter_model)
            return content
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("ai_summary_failed_using_fallback", error=str(exc))
        return _fallback_summary(context)
