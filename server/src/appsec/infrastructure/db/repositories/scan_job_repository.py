import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.scan_job import ScanJob
from appsec.infrastructure.db.models.scan_job import ScanJobModel


def _to_entity(model: ScanJobModel) -> ScanJob:
    return ScanJob(
        id=model.id,
        project_id=model.project_id,
        organization_id=model.organization_id,
        domain_id=model.domain_id,
        status=model.status,
        scan_type=model.scan_type,
        created_by=model.created_by,
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
    )


class SqlAlchemyScanJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, scan_job_id: uuid.UUID, organization_id: uuid.UUID) -> ScanJob | None:
        result = await self._session.execute(
            select(ScanJobModel).where(
                ScanJobModel.id == scan_job_id, ScanJobModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, scan_job: ScanJob) -> ScanJob:
        model = ScanJobModel(
            id=scan_job.id,
            project_id=scan_job.project_id,
            organization_id=scan_job.organization_id,
            domain_id=scan_job.domain_id,
            status=scan_job.status,
            scan_type=scan_job.scan_type,
            created_by=scan_job.created_by,
            started_at=scan_job.started_at,
            completed_at=scan_job.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, scan_job: ScanJob) -> ScanJob:
        model = await self._session.get(ScanJobModel, scan_job.id)
        if model is None:
            raise ValueError(f"ScanJob {scan_job.id} not found")
        model.status = scan_job.status
        model.started_at = scan_job.started_at
        model.completed_at = scan_job.completed_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_project(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> list[ScanJob]:
        result = await self._session.execute(
            select(ScanJobModel).where(
                ScanJobModel.project_id == project_id, ScanJobModel.organization_id == organization_id
            )
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[ScanJob]:
        result = await self._session.execute(
            select(ScanJobModel).where(ScanJobModel.organization_id == organization_id)
        )
        return [_to_entity(m) for m in result.scalars().all()]
