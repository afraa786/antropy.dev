import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.project import Project
from appsec.infrastructure.db.models.project import ProjectModel


def _to_entity(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        created_at=model.created_at,
    )


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> Project | None:
        result = await self._session.execute(
            select(ProjectModel).where(
                ProjectModel.id == project_id, ProjectModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, project: Project) -> Project:
        model = ProjectModel(
            id=project.id,
            organization_id=project.organization_id,
            name=project.name,
            description=project.description,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Project]:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.organization_id == organization_id)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def delete(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(ProjectModel).where(
                ProjectModel.id == project_id, ProjectModel.organization_id == organization_id
            )
        )
