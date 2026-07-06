import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.report import Report
from appsec.domain.enums import ReportFormat, ReportStatus
from appsec.domain.exceptions import ForbiddenError, NotFoundError
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.report_repository import ReportRepository
from appsec.domain.repositories.scan_job_repository import ScanJobRepository


class ReportService:
    def __init__(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
        scan_job_repository: ScanJobRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._session = session
        self._reports = report_repository
        self._scan_jobs = scan_job_repository
        self._orgs = organization_repository

    async def create_for_scan_job(
        self,
        scan_job_id: uuid.UUID,
        organization_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        report_format: ReportFormat,
    ) -> Report:
        await self._require_member(organization_id, requesting_user_id)

        scan_job = await self._scan_jobs.get_by_id(scan_job_id, organization_id)
        if scan_job is None:
            raise NotFoundError(f"ScanJob {scan_job_id} not found")

        report = Report(
            id=uuid.uuid4(),
            organization_id=organization_id,
            project_id=scan_job.project_id,
            scan_job_id=scan_job_id,
            format=report_format,
            status=ReportStatus.PENDING,
            file_path=None,
            generated_at=None,
            created_at=datetime.now(UTC),
        )
        created = await self._reports.create(report)
        await self._session.commit()
        # Report generation (rendering/upload) is out of scope for this foundation.
        return created

    async def get_by_id(
        self, report_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> Report:
        await self._require_member(organization_id, requesting_user_id)
        report = await self._reports.get_by_id(report_id, organization_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found")
        return report

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
