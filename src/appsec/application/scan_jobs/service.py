import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.scan_job import ScanJob
from appsec.domain.enums import ScanStatus
from appsec.domain.exceptions import DomainNotVerifiedError, ForbiddenError, NotFoundError
from appsec.domain.repositories.domain_repository import DomainRepository
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.project_repository import ProjectRepository
from appsec.domain.repositories.scan_job_repository import ScanJobRepository
from appsec.infrastructure.tasks.scan_execution import execute_scan_job


class ScanJobService:
    def __init__(
        self,
        session: AsyncSession,
        scan_job_repository: ScanJobRepository,
        domain_repository: DomainRepository,
        project_repository: ProjectRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._session = session
        self._scan_jobs = scan_job_repository
        self._domains = domain_repository
        self._projects = project_repository
        self._orgs = organization_repository

    async def create(
        self,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        domain_id: uuid.UUID,
        scan_type: str,
    ) -> ScanJob:
        await self._require_member(organization_id, requesting_user_id)

        project = await self._projects.get_by_id(project_id, organization_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")

        domain = await self._domains.get_by_id(domain_id, organization_id)
        if domain is None:
            raise NotFoundError(f"Domain {domain_id} not found")

        # Hard gate: never allow scanning an unverified domain, regardless of caller intent.
        if not domain.is_verified:
            raise DomainNotVerifiedError(domain.hostname)

        scan_job = ScanJob(
            id=uuid.uuid4(),
            project_id=project_id,
            organization_id=organization_id,
            domain_id=domain_id,
            status=ScanStatus.PENDING,
            scan_type=scan_type,
            created_by=requesting_user_id,
            created_at=datetime.now(UTC),
            started_at=None,
            completed_at=None,
        )
        created = await self._scan_jobs.create(scan_job)
        await self._session.commit()
        execute_scan_job.delay(str(created.id))
        return created

    async def get_by_id(
        self, scan_job_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> ScanJob:
        await self._require_member(organization_id, requesting_user_id)
        scan_job = await self._scan_jobs.get_by_id(scan_job_id, organization_id)
        if scan_job is None:
            raise NotFoundError(f"ScanJob {scan_job_id} not found")
        return scan_job

    async def list_for_project(
        self, project_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[ScanJob]:
        await self._require_member(organization_id, requesting_user_id)
        return await self._scan_jobs.list_for_project(project_id, organization_id)

    async def list_for_organization(
        self, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[ScanJob]:
        await self._require_member(organization_id, requesting_user_id)
        return await self._scan_jobs.list_for_organization(organization_id)

    async def cancel(
        self, scan_job_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> ScanJob:
        scan_job = await self.get_by_id(scan_job_id, organization_id, requesting_user_id)
        if scan_job.status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED):
            return scan_job
        scan_job.status = ScanStatus.CANCELLED
        scan_job.completed_at = datetime.now(UTC)
        updated = await self._scan_jobs.update(scan_job)
        await self._session.commit()
        return updated

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
