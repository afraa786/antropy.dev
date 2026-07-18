"""Progressive urlscan.io scan task. Runs *after* the main scan job has already
been marked completed by the fast engines, so a slow (~2 min) urlscan result
never delays job completion. When urlscan lands, its findings are appended as an
additional ScanResultModel row against the same scan_job_id.
"""

import asyncio
import uuid
from datetime import UTC, datetime

from appsec.config import get_settings
from appsec.infrastructure.celery_app import celery_app
from appsec.infrastructure.db.models.domain import DomainModel
from appsec.infrastructure.db.models.scan_job import ScanJobModel
from appsec.infrastructure.db.models.scan_result import ScanResultModel
from appsec.infrastructure.db.sync_session import get_sync_session
from appsec.logging import get_logger
from appsec.scanner.orchestrator import run_single_engine
from appsec.scanner.reports.formatter import format_report

logger = get_logger(__name__)


@celery_app.task(name="scan.urlscan", bind=True, max_retries=0)
def execute_urlscan(self, scan_job_id: str) -> None:
    if not get_settings().urlscan_api_key:
        logger.info("urlscan_skipped_no_key", scan_job_id=scan_job_id)
        return

    with get_sync_session() as session:
        scan_job = session.get(ScanJobModel, scan_job_id)
        if scan_job is None:
            logger.warning("urlscan_scan_job_not_found", scan_job_id=scan_job_id)
            return
        domain = session.get(DomainModel, scan_job.domain_id)
        if domain is None:
            logger.warning("urlscan_domain_missing", scan_job_id=scan_job_id)
            return

        try:
            output = asyncio.run(
                run_single_engine(
                    engine_name="urlscan",
                    scan_job_id=uuid.UUID(scan_job_id),
                    organization_id=scan_job.organization_id,
                    hostname=domain.hostname,
                )
            )
        except Exception as exc:  # noqa: BLE001 -- never crash the worker on a slow engine
            logger.error("urlscan_execution_failed", scan_job_id=scan_job_id, error=str(exc))
            return

        report = format_report(output)
        summary = {
            **report["summary"],
            "engine": "urlscan",
            "partial": True,  # appended after job completion
            "appended_at": datetime.now(UTC).isoformat(),
        }
        result = ScanResultModel(
            id=uuid.uuid4(),
            scan_job_id=scan_job.id,
            organization_id=scan_job.organization_id,
            summary=summary,
            severity_counts=output.severity_counts,
        )
        session.add(result)
        session.commit()

        logger.info(
            "urlscan_result_appended",
            scan_job_id=scan_job_id,
            finding_count=len(output.findings),
        )
