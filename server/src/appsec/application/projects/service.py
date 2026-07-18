import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.project import Project
from appsec.domain.exceptions import ForbiddenError, NotFoundError
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        project_repository: ProjectRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._session = session
        self._projects = project_repository
        self._orgs = organization_repository

    async def create(
        self, organization_id: uuid.UUID, requesting_user_id: uuid.UUID, name: str, description: str | None
    ) -> Project:
        await self._require_member(organization_id, requesting_user_id)
        project = Project(
            id=uuid.uuid4(),
            organization_id=organization_id,
            name=name,
            description=description,
            created_at=datetime.now(UTC),
        )
        created = await self._projects.create(project)
        await self._session.commit()
        return created

    async def get_by_id(
        self, project_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> Project:
        await self._require_member(organization_id, requesting_user_id)
        project = await self._projects.get_by_id(project_id, organization_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def list_for_organization(
        self, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[Project]:
        await self._require_member(organization_id, requesting_user_id)
        return await self._projects.list_for_organization(organization_id)

    async def delete(
        self, project_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> None:
        await self._require_member(organization_id, requesting_user_id)
        await self._projects.delete(project_id, organization_id)
        await self._session.commit()

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
