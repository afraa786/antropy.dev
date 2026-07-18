import uuid
from typing import Protocol

from appsec.domain.entities.organization import Organization, OrganizationMember
from appsec.domain.enums import OrganizationRole


class OrganizationRepository(Protocol):
    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None: ...

    async def get_by_slug(self, slug: str) -> Organization | None: ...

    async def create(self, organization: Organization) -> Organization: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]: ...

    async def add_member(self, member: OrganizationMember) -> OrganizationMember: ...

    async def get_member(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMember | None: ...

    async def list_members(self, organization_id: uuid.UUID) -> list[OrganizationMember]: ...

    async def get_member_role(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationRole | None: ...
