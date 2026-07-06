"""Runs selected engines against a target and collects their results. Knows
how to call `Scanner.validate()` / `health_check()` / `scan()` — nothing
about any specific tool. Async-first: engines run concurrently.
"""

import asyncio

from appsec.logging import get_logger
from appsec.scanner.interfaces.models import ScanResult, Target
from appsec.scanner.interfaces.registry import get_scanner

logger = get_logger(__name__)


async def _run_engine(engine_name: str, target: Target) -> ScanResult:
    scanner_cls = get_scanner(engine_name)
    scanner = scanner_cls()

    if not await scanner.health_check():
        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=engine_name,
            success=False,
            error_message=f"Engine '{engine_name}' failed health check",
        )

    if not await scanner.validate(target):
        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=engine_name,
            success=False,
            error_message=f"Engine '{engine_name}' rejected target '{target.hostname}'",
        )

    try:
        return await scanner.scan(target)
    except Exception as exc:  # noqa: BLE001 -- isolate one engine's failure from the batch
        logger.error("engine_scan_failed", engine=engine_name, error=str(exc))
        return ScanResult(
            scan_job_id=target.scan_job_id,
            engine=engine_name,
            success=False,
            error_message=str(exc),
        )


async def dispatch(engine_names: list[str], target: Target) -> list[ScanResult]:
    """Runs every named engine concurrently against `target`. One engine's
    failure never blocks the others — each returns its own success/failure
    `ScanResult`.
    """
    if not engine_names:
        return []
    return await asyncio.gather(*(_run_engine(name, target) for name in engine_names))
