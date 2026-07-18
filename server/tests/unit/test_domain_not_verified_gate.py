import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from appsec.application.scan_jobs.service import ScanJobService
from appsec.domain.entities.domain import Domain
from appsec.domain.entities.project import Project
from appsec.domain.enums import OrganizationRole, VerificationMethod, VerificationStatus
from appsec.domain.exceptions import DomainNotVerifiedError


@pytest.mark.asyncio
async def test_scan_job_creation_rejected_for_unverified_domain() -> None:
    organization_id = uuid.uuid4()
    project_id = uuid.uuid4()
    domain_id = uuid.uuid4()
    user_id = uuid.uuid4()

    unverified_domain = Domain(
        id=domain_id,
        project_id=project_id,
        organization_id=organization_id,
        hostname="example.com",
        verification_status=VerificationStatus.PENDING,
        verification_method=VerificationMethod.DNS_TXT,
        verification_token="abc123",
        verified_at=None,
        created_at=datetime.now(UTC),
    )
    project = Project(
        id=project_id,
        organization_id=organization_id,
        name="Test Project",
        description=None,
        created_at=datetime.now(UTC),
    )

    org_repo = AsyncMock()
    org_repo.get_member_role.return_value = OrganizationRole.MEMBER

    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project

    domain_repo = AsyncMock()
    domain_repo.get_by_id.return_value = unverified_domain

    scan_job_repo = AsyncMock()

    service = ScanJobService(
        session=AsyncMock(),
        scan_job_repository=scan_job_repo,
        domain_repository=domain_repo,
        project_repository=project_repo,
        organization_repository=org_repo,
    )

    with pytest.raises(DomainNotVerifiedError):
        await service.create(project_id, organization_id, user_id, domain_id, "default")

    scan_job_repo.create.assert_not_called()
