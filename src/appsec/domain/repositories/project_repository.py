import uuid
from typing import Protocol

from appsec.domain.entities.project import Project


class ProjectRepository(Protocol):
    async def get_by_id(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> Project | None: ...

    async def create(self, project: Project) -> Project: ...

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[Project]: ...

    async def delete(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> None: ...
