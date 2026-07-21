"""Runs selected engines against a target and collects their results. Knows
how to call `Scanner.validate()` / `health_check()` / `scan()` — nothing
about any specific tool. Async-first: engines within a stage run concurrently;
`dispatch_staged` runs ordered stages so one stage's output can feed the next.
"""

import asyncio
import contextlib
import dataclasses
import os

from appsec.logging import get_logger
from appsec.scanner.interfaces.models import ScanResult, Target
from appsec.scanner.interfaces.registry import get_scanner

logger = get_logger(__name__)

#: Maps an artifact key produced by an upstream engine to the Target.options key
#: a downstream engine reads. E.g. katana publishes artifacts["urls_file"];
#: nuclei consumes options["nuclei_url_list"]. Extend this as engines chain.
_ARTIFACT_TO_OPTION = {
    "urls_file": "nuclei_url_list",
}


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


async def dispatch_staged(stages: list[list[str]], target: Target) -> list[ScanResult]:
    """Runs engines stage by stage. Engines within a stage run concurrently
    (like `dispatch`); stages run in order. After each stage, any artifacts an
    engine published (e.g. katana's crawled-URL file) are injected into the
    `Target.options` handed to the next stage — this is how katana feeds nuclei.

    Temp files forwarded between stages are cleaned up once the whole run ends.
    """
    all_results: list[ScanResult] = []
    # Copy options so we never mutate the caller's Target; carry forwarded keys.
    forwarded_options = dict(target.options)
    forwarded_files: list[str] = []

    try:
        for stage in stages:
            if not stage:
                continue
            stage_target = dataclasses.replace(target, options=dict(forwarded_options))
            results = await asyncio.gather(*(_run_engine(name, stage_target) for name in stage))
            all_results.extend(results)

            # Collect artifacts this stage produced and map them to the option
            # keys the next stage's engines read.
            for result in results:
                for artifact_key, value in result.artifacts.items():
                    option_key = _ARTIFACT_TO_OPTION.get(artifact_key)
                    if option_key and value:
                        forwarded_options[option_key] = value
                        forwarded_files.append(value)
                        logger.info(
                            "stage_artifact_forwarded",
                            engine=result.engine,
                            artifact=artifact_key,
                            option=option_key,
                        )
        return all_results
    finally:
        # The dispatcher owns forwarded files (the producing engine deliberately
        # did not delete them); clean them up now the pipeline is done.
        for path in forwarded_files:
            await asyncio.to_thread(_unlink_quiet, path)


def _unlink_quiet(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)
