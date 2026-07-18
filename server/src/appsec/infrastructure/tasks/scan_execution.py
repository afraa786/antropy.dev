"""Celery entry point for running a scan job. This module is the only place
in `infrastructure/` that touches the scanner subsystem, and it only calls
`scanner.orchestrator.run_scan()` — it has no knowledge of Nuclei, Katana, or
any other engine. Engines are resolved dynamically via the scanner registry.
"""

import asyncio
import uuid
from datetime import UTC, datetime

from appsec.domain.enums import ScanStatus
from appsec.infrastructure.celery_app import celery_app
from appsec.infrastructure.db.models.domain import DomainModel
from appsec.infrastructure.db.models.scan_job import ScanJobModel
from appsec.infrastructure.db.models.scan_result import ScanResultModel
from appsec.infrastructure.db.sync_session import get_sync_session
from appsec.logging import get_logger
from appsec.scanner.orchestrator import run_scan
from appsec.scanner.reports.ai_summary import generate_summary
from appsec.scanner.reports.formatter import format_report

logger = get_logger(__name__)


@celery_app.task(name="scan.execute", bind=True, max_retries=1)
def execute_scan_job(self, scan_job_id: str) -> None:
    with get_sync_session() as session:
        scan_job = session.get(ScanJobModel, scan_job_id)
        if scan_job is None:
            logger.warning("scan_job_not_found", scan_job_id=scan_job_id)
            return

        domain = session.get(DomainModel, scan_job.domain_id)
        if domain is None:
            logger.warning("scan_job_domain_missing", scan_job_id=scan_job_id)
            return

        scan_job.status = ScanStatus.RUNNING
        scan_job.started_at = datetime.now(UTC)
        session.commit()

        async def _run_and_summarize():
            output = await run_scan(
                scan_job_id=uuid.UUID(scan_job_id),
                organization_id=scan_job.organization_id,
                hostname=domain.hostname,
                scan_type=scan_job.scan_type,
            )
            ai_summary = await generate_summary(output)
            return output, ai_summary

        try:
            output, ai_summary = asyncio.run(_run_and_summarize())
        except Exception as exc:  # noqa: BLE001 -- persist failure state, don't crash worker
            logger.error("scan_job_execution_failed", scan_job_id=scan_job_id, error=str(exc))
            scan_job.status = ScanStatus.FAILED
            scan_job.completed_at = datetime.now(UTC)
            session.commit()
            return

        report = format_report(output)
        summary = {**report["summary"], "ai_summary": ai_summary}
        result = ScanResultModel(
            id=uuid.uuid4(),
            scan_job_id=scan_job.id,
            organization_id=scan_job.organization_id,
            summary=summary,
            severity_counts=output.severity_counts,
        )
        session.add(result)

        scan_job.status = ScanStatus.COMPLETED
        scan_job.completed_at = datetime.now(UTC)
        session.commit()

        logger.info(
            "scan_job_completed",
            scan_job_id=scan_job_id,
            finding_count=len(output.findings),
        )
