"""Single entry point the SaaS backend uses to run a scan. The API/Celery
layer calls `run_scan()` and nothing else — it never imports a specific
engine, the registry, the dispatcher, or the pipeline directly. This is the
seam that keeps scanner development fully decoupled from the backend: as
long as `run_scan()`'s signature and `PipelineOutput` shape stay stable,
engines can be added, replaced, or reworked with zero backend changes.
"""

import uuid

from appsec.logging import get_logger
from appsec.scanner.events import ScanFailed, ScanFinished, ScanStarted
from appsec.scanner.interfaces.models import Target
from appsec.scanner.orchestrator.dispatcher import dispatch
from appsec.scanner.orchestrator.pipeline import PipelineOutput, process
from appsec.scanner.orchestrator.scheduler import select_engines


async def run_single_engine(
    engine_name: str,
    scan_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    hostname: str,
) -> PipelineOutput:
    """Runs exactly one named engine and returns its normalized output. Used by
    progressive engines (e.g. urlscan) that execute in their own task after the
    main scan has already completed.
    """
    target = Target(hostname=hostname, scan_job_id=scan_job_id, organization_id=organization_id)
    results = await dispatch([engine_name], target)
    return process(results)

logger = get_logger(__name__)


async def run_scan(
    scan_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    hostname: str,
    scan_type: str = "default",
) -> PipelineOutput:
    """Selects engines for `scan_type`, runs them against `hostname`
    concurrently, and returns normalized findings. Emits scan lifecycle
    events (started/finished/failed) — callers (Celery task, notification
    service) subscribe to those rather than reaching into engine internals.

    Returns an empty `PipelineOutput` (zero findings, zero failed engines)
    if no engines are registered yet — this is expected until scanner
    adapters are implemented and registered under `scanner/engines/`.
    """
    engine_names = select_engines(scan_type)

    logger.info(
        "scan_started", scan_job_id=str(scan_job_id), engines=engine_names, scan_type=scan_type
    )
    started_event = ScanStarted(
        scan_job_id=scan_job_id, organization_id=organization_id, engines=engine_names
    )
    logger.info("scan_event", payload=started_event)

    if not engine_names:
        logger.warning("scan_no_engines_registered", scan_job_id=str(scan_job_id))
        return PipelineOutput(findings=[], counts={}, failed_engines=[])

    target = Target(hostname=hostname, scan_job_id=scan_job_id, organization_id=organization_id)

    try:
        results = await dispatch(engine_names, target)
    except Exception as exc:  # noqa: BLE001 -- surface as a scan-level failure event
        logger.error("scan_failed", scan_job_id=str(scan_job_id), error=str(exc))
        failed_event = ScanFailed(
            scan_job_id=scan_job_id,
            organization_id=organization_id,
            engine=None,
            error_message=str(exc),
        )
        logger.info("scan_event", payload=failed_event)
        raise

    output = process(results)

    finished_event = ScanFinished(
        scan_job_id=scan_job_id,
        organization_id=organization_id,
        engines=engine_names,
        finding_count=len(output.findings),
        severity_counts=output.severity_counts,
    )
    logger.info("scan_event", payload=finished_event)

    return output
