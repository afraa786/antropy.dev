import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.config import get_settings
from appsec.domain.entities.domain import Domain
from appsec.domain.enums import VerificationMethod, VerificationStatus
from appsec.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from appsec.domain.repositories.domain_repository import DomainRepository
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.project_repository import ProjectRepository
from appsec.infrastructure.tasks.domain_verification import check_domain_verification


class DomainService:
    def __init__(
        self,
        session: AsyncSession,
        domain_repository: DomainRepository,
        project_repository: ProjectRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._session = session
        self._domains = domain_repository
        self._projects = project_repository
        self._orgs = organization_repository

    async def create(
        self,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        hostname: str,
        verification_method: VerificationMethod,
    ) -> Domain:
        await self._require_member(organization_id, requesting_user_id)

        project = await self._projects.get_by_id(project_id, organization_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")

        existing = await self._domains.get_by_hostname(hostname, organization_id)
        if existing is not None:
            raise ConflictError(f"Domain '{hostname}' already registered for this organization")

        domain = Domain(
            id=uuid.uuid4(),
            project_id=project_id,
            organization_id=organization_id,
            hostname=hostname,
            verification_status=VerificationStatus.PENDING,
            verification_method=verification_method,
            verification_token=secrets.token_hex(16),
            verified_at=None,
            created_at=datetime.now(UTC),
        )
        created = await self._domains.create(domain)
        await self._session.commit()
        return created

    async def get_by_id(
        self, domain_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> Domain:
        await self._require_member(organization_id, requesting_user_id)
        domain = await self._domains.get_by_id(domain_id, organization_id)
        if domain is None:
            raise NotFoundError(f"Domain {domain_id} not found")
        return domain

    def verification_instructions(self, domain: Domain) -> dict:
        settings = get_settings()
        if domain.verification_method == VerificationMethod.DNS_TXT:
            return {
                "domain_id": domain.id,
                "method": domain.verification_method,
                "dns_txt_record_name": f"_{settings.verification_token_prefix}.{domain.hostname}",
                "dns_txt_record_value": f"{settings.verification_token_prefix}={domain.verification_token}",
            }
        return {
            "domain_id": domain.id,
            "method": domain.verification_method,
            "http_file_url": (
                f"http://{domain.hostname}/.well-known/{settings.verification_token_prefix}/"
                f"{domain.verification_token}.txt"
            ),
            "http_file_content": domain.verification_token,
        }

    async def initiate_verification(
        self, domain_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> Domain:
        """Queues an async verification check; caller polls status separately."""
        domain = await self.get_by_id(domain_id, organization_id, requesting_user_id)
        check_domain_verification.delay(str(domain.id))
        return domain

    async def check_verification_status(
        self, domain_id: uuid.UUID, organization_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> Domain:
        """Re-reads current status (task runs async in worker)."""
        return await self.get_by_id(domain_id, organization_id, requesting_user_id)

    async def _require_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._orgs.get_member_role(organization_id, user_id)
        if role is None:
            raise ForbiddenError("Not a member of this organization")
