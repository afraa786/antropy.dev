"""One-call scan bootstrap. Hides the org -> project -> domain -> verify ->
scan-job sequence behind a single entry point so the frontend only sends a
target. Everything here composes the existing per-resource services, so their
membership checks, commits, and the domain-verified scan gate all still apply.
"""

import uuid
from datetime import UTC, datetime

from appsec.application.domains.service import DomainService
from appsec.application.organizations.service import OrganizationService
from appsec.application.projects.service import ProjectService
from appsec.application.scan_jobs.service import ScanJobService
from appsec.config import get_settings
from appsec.domain.entities.scan_job import ScanJob
from appsec.domain.enums import VerificationMethod, VerificationStatus
from appsec.domain.exceptions import ForbiddenError, NotFoundError
from appsec.domain.repositories.domain_repository import DomainRepository
from appsec.domain.repositories.organization_repository import OrganizationRepository
from appsec.domain.repositories.project_repository import ProjectRepository
from appsec.domain.repositories.user_repository import UserRepository


def _workspace_slug(user_id: uuid.UUID) -> str:
    """Deterministic slug for a user's auto-created default workspace, so
    repeated quick-scans reuse the same org instead of creating new ones.
    Slug must satisfy the org ``^[a-z0-9-]+$`` constraint.
    """
    return f"ws-{user_id.hex[:12]}"


class QuickScanService:
    def __init__(
        self,
        organization_service: OrganizationService,
        project_service: ProjectService,
        domain_service: DomainService,
        scan_job_service: ScanJobService,
        organization_repository: OrganizationRepository,
        project_repository: ProjectRepository,
        domain_repository: DomainRepository,
        user_repository: UserRepository,
    ) -> None:
        self._org_service = organization_service
        self._project_service = project_service
        self._domain_service = domain_service
        self._scan_job_service = scan_job_service
        self._orgs = organization_repository
        self._projects = project_repository
        self._domains = domain_repository
        self._users = user_repository

    async def run(
        self,
        user_id: uuid.UUID,
        target: str,
        target_type: str,
        scan_type: str,
        skip_verification: bool,
    ) -> ScanJob:
        if target_type != "domain":
            raise ForbiddenError(
                f"target_type '{target_type}' is not supported yet — only 'domain'."
            )
        hostname = target.strip().lower()

        organization = await self._get_or_create_workspace(user_id)
        project = await self._get_or_create_project(organization.id, user_id, hostname)
        domain = await self._get_or_create_domain(project.id, organization.id, user_id, hostname)

        if not domain.is_verified:
            await self._maybe_skip_verification(domain, skip_verification)

        scan_job = await self._scan_job_service.create(
            project.id, organization.id, user_id, domain.id, scan_type
        )
        return scan_job

    async def _get_or_create_workspace(self, user_id: uuid.UUID):
        slug = _workspace_slug(user_id)
        existing = await self._orgs.get_by_slug(slug)
        if existing is not None:
            return existing

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        name = f"{user.email}'s Workspace"
        return await self._org_service.create(name, slug, user_id)

    async def _get_or_create_project(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, hostname: str
    ):
        for project in await self._projects.list_for_organization(organization_id):
            if project.name == hostname:
                return project
        return await self._project_service.create(
            organization_id, user_id, name=hostname, description=f"Auto-created for {hostname}"
        )

    async def _get_or_create_domain(
        self,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        hostname: str,
    ):
        existing = await self._domains.get_by_hostname(hostname, organization_id)
        if existing is not None:
            return existing
        return await self._domain_service.create(
            project_id, organization_id, user_id, hostname, VerificationMethod.DNS_TXT
        )

    async def _maybe_skip_verification(self, domain, skip_verification: bool) -> None:
        if not skip_verification:
            return
        if not get_settings().allow_demo_verification_skip:
            raise ForbiddenError(
                "skip_verification is not permitted in this environment "
                "(ALLOW_DEMO_VERIFICATION_SKIP is not enabled)."
            )
        domain.verification_status = VerificationStatus.VERIFIED
        domain.verified_at = datetime.now(UTC)
        await self._domains.update(domain)
