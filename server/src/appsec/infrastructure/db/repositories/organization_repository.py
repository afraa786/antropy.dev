import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.organization import Organization, OrganizationMember
from appsec.domain.enums import OrganizationRole
from appsec.infrastructure.db.models.organization import OrganizationMemberModel, OrganizationModel


def _to_org_entity(model: OrganizationModel) -> Organization:
    return Organization(id=model.id, name=model.name, slug=model.slug, created_at=model.created_at)


def _to_member_entity(model: OrganizationMemberModel) -> OrganizationMember:
    return OrganizationMember(
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=model.role,
        joined_at=model.joined_at,
    )


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        model = await self._session.get(OrganizationModel, organization_id)
        return _to_org_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._session.execute(select(OrganizationModel).where(OrganizationModel.slug == slug))
        model = result.scalar_one_or_none()
        return _to_org_entity(model) if model else None

    async def create(self, organization: Organization) -> Organization:
        model = OrganizationModel(id=organization.id, name=organization.name, slug=organization.slug)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_org_entity(model)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        result = await self._session.execute(
            select(OrganizationModel)
            .join(OrganizationMemberModel, OrganizationMemberModel.organization_id == OrganizationModel.id)
            .where(OrganizationMemberModel.user_id == user_id)
        )
        return [_to_org_entity(m) for m in result.scalars().all()]

    async def add_member(self, member: OrganizationMember) -> OrganizationMember:
        model = OrganizationMemberModel(
            organization_id=member.organization_id, user_id=member.user_id, role=member.role
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_member_entity(model)

    async def get_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationMember | None:
        model = await self._session.get(OrganizationMemberModel, (organization_id, user_id))
        return _to_member_entity(model) if model else None

    async def list_members(self, organization_id: uuid.UUID) -> list[OrganizationMember]:
        result = await self._session.execute(
            select(OrganizationMemberModel).where(OrganizationMemberModel.organization_id == organization_id)
        )
        return [_to_member_entity(m) for m in result.scalars().all()]

    async def get_member_role(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationRole | None:
        member = await self.get_member(organization_id, user_id)
        return member.role if member else None
