import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.scan_result import ScanResult
from appsec.infrastructure.db.models.scan_result import ScanResultModel


def _to_entity(model: ScanResultModel) -> ScanResult:
    return ScanResult(
        id=model.id,
        scan_job_id=model.scan_job_id,
        organization_id=model.organization_id,
        summary=model.summary,
        severity_counts=model.severity_counts,
        created_at=model.created_at,
    )


class SqlAlchemyScanResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_scan_job(
        self, scan_job_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ScanResult]:
        result = await self._session.execute(
            select(ScanResultModel).where(
                ScanResultModel.scan_job_id == scan_job_id,
                ScanResultModel.organization_id == organization_id,
            )
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def create(self, scan_result: ScanResult) -> ScanResult:
        model = ScanResultModel(
            id=scan_result.id,
            scan_job_id=scan_result.scan_job_id,
            organization_id=scan_result.organization_id,
            summary=scan_result.summary,
            severity_counts=scan_result.severity_counts,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
