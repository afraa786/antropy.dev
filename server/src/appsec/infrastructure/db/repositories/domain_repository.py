import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.domain import Domain
from appsec.infrastructure.db.models.domain import DomainModel


def _to_entity(model: DomainModel) -> Domain:
    return Domain(
        id=model.id,
        project_id=model.project_id,
        organization_id=model.organization_id,
        hostname=model.hostname,
        verification_status=model.verification_status,
        verification_method=model.verification_method,
        verification_token=model.verification_token,
        verified_at=model.verified_at,
        created_at=model.created_at,
    )


class SqlAlchemyDomainRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, domain_id: uuid.UUID, organization_id: uuid.UUID) -> Domain | None:
        result = await self._session.execute(
            select(DomainModel).where(
                DomainModel.id == domain_id, DomainModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_hostname(self, hostname: str, organization_id: uuid.UUID) -> Domain | None:
        result = await self._session.execute(
            select(DomainModel).where(
                DomainModel.hostname == hostname, DomainModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, domain: Domain) -> Domain:
        model = DomainModel(
            id=domain.id,
            project_id=domain.project_id,
            organization_id=domain.organization_id,
            hostname=domain.hostname,
            verification_status=domain.verification_status,
            verification_method=domain.verification_method,
            verification_token=domain.verification_token,
            verified_at=domain.verified_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, domain: Domain) -> Domain:
        model = await self._session.get(DomainModel, domain.id)
        if model is None:
            raise ValueError(f"Domain {domain.id} not found")
        model.verification_status = domain.verification_status
        model.verification_method = domain.verification_method
        model.verification_token = domain.verification_token
        model.verified_at = domain.verified_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_project(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> list[Domain]:
        result = await self._session.execute(
            select(DomainModel).where(
                DomainModel.project_id == project_id, DomainModel.organization_id == organization_id
            )
        )
        return [_to_entity(m) for m in result.scalars().all()]
