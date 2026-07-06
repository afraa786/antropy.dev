import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.report import Report
from appsec.infrastructure.db.models.report import ReportModel


def _to_entity(model: ReportModel) -> Report:
    return Report(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        scan_job_id=model.scan_job_id,
        format=model.format,
        status=model.status,
        file_path=model.file_path,
        generated_at=model.generated_at,
        created_at=model.created_at,
    )


class SqlAlchemyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, report_id: uuid.UUID, organization_id: uuid.UUID) -> Report | None:
        result = await self._session.execute(
            select(ReportModel).where(
                ReportModel.id == report_id, ReportModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, report: Report) -> Report:
        model = ReportModel(
            id=report.id,
            organization_id=report.organization_id,
            project_id=report.project_id,
            scan_job_id=report.scan_job_id,
            format=report.format,
            status=report.status,
            file_path=report.file_path,
            generated_at=report.generated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, report: Report) -> Report:
        model = await self._session.get(ReportModel, report.id)
        if model is None:
            raise ValueError(f"Report {report.id} not found")
        model.status = report.status
        model.file_path = report.file_path
        model.generated_at = report.generated_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
