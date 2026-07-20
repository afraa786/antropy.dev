import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_domain_service
from appsec.application.domains.schemas import (
    CreateDomainRequest,
    DomainResponse,
    VerificationInstructionsResponse,
)
from appsec.application.domains.service import DomainService

router = APIRouter(tags=["domains"])


def _to_response(domain) -> DomainResponse:  # noqa: ANN001
    return DomainResponse(
        id=domain.id,
        project_id=domain.project_id,
        organization_id=domain.organization_id,
        hostname=domain.hostname,
        verification_status=domain.verification_status,
        verification_method=domain.verification_method,
        verification_token=domain.verification_token,
        verified_at=domain.verified_at,
        created_at=domain.created_at,
    )


@router.post(
    "/projects/{project_id}/domains",
    response_model=DomainResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_domain(
    project_id: uuid.UUID,
    payload: CreateDomainRequest,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> DomainResponse:
    domain = await domain_service.create(
        project_id, organization_id, user_id, payload.hostname, payload.verification_method
    )
    return _to_response(domain)


@router.get("/domains/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> DomainResponse:
    domain = await domain_service.get_by_id(domain_id, organization_id, user_id)
    return _to_response(domain)


@router.post("/domains/{domain_id}/verify/initiate", response_model=VerificationInstructionsResponse)
async def initiate_domain_verification(
    domain_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> VerificationInstructionsResponse:
    domain = await domain_service.initiate_verification(domain_id, organization_id, user_id)
    instructions = domain_service.verification_instructions(domain)
    return VerificationInstructionsResponse(**instructions)


@router.post("/domains/{domain_id}/verify/check", response_model=DomainResponse)
async def check_domain_verification(
    domain_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> DomainResponse:
    domain = await domain_service.check_verification_status(domain_id, organization_id, user_id)
    return _to_response(domain)
