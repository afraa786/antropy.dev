import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.organization import Organization, OrganizationMember
from appsec.domain.enums import OrganizationRole
from appsec.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from appsec.domain.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    def __init__(self, session: AsyncSession, organization_repository: OrganizationRepository) -> None:
        self._session = session
        self._orgs = organization_repository

    async def create(self, name: str, slug: str, owner_id: uuid.UUID) -> Organization:
        existing = await self._orgs.get_by_slug(slug)
        if existing is not None:
            raise ConflictError(f"Organization slug '{slug}' already taken")

        organization = Organization(
            id=uuid.uuid4(), name=name, slug=slug, created_at=datetime.now(UTC)
        )
        created = await self._orgs.create(organization)
        await self._orgs.add_member(
            OrganizationMember(
                organization_id=created.id,
                user_id=owner_id,
                role=OrganizationRole.OWNER,
                joined_at=datetime.now(UTC),
            )
        )
        await self._session.commit()
        return created

    async def get_by_id(self, organization_id: uuid.UUID, requesting_user_id: uuid.UUID) -> Organization:
        await self._require_member(organization_id, requesting_user_id)
        organization = await self._orgs.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization {organization_id} not found")
        return organization

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        return await self._orgs.list_for_user(user_id)

    async def add_member(
        self,
        organization_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: OrganizationRole,
    ) -> OrganizationMember:
        allowed_roles = {OrganizationRole.OWNER, OrganizationRole.ADMIN}
        await self._require_role(organization_id, requesting_user_id, allowed_roles)

        existing = await self._orgs.get_member(organization_id, target_user_id)
        if existing is not None:
            raise ConflictError("User is already a member of this organization")

        member = await self._orgs.add_member(
            OrganizationMember(
                organization_id=organization_id,
                user_id=target_user_id,
                role=role,
                joined_at=datetime.now(UTC),
            )
        )
        await self._session.commit()
        return member

    async def list_members(
        self, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[OrganizationMember]:
        await self._require_member(organization_id, requesting_user_id)
        return await self._orgs.list_members(organization_id)

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationRole:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
        return role

    async def _require_role(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, allowed: set[OrganizationRole]
    ) -> None:
        role = await self._require_member(organization_id, user_id)
        if role not in allowed:
            raise ForbiddenError("Insufficient permissions for this action")
