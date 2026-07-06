import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentUserIdDep, get_organization_service
from appsec.application.organizations.schemas import (
    AddMemberRequest,
    CreateOrganizationRequest,
    MemberResponse,
    OrganizationResponse,
)
from appsec.application.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: CreateOrganizationRequest,
    user_id: CurrentUserIdDep,
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationResponse:
    org = await org_service.create(payload.name, payload.slug, user_id)
    return OrganizationResponse(id=org.id, name=org.name, slug=org.slug, created_at=org.created_at)


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    user_id: CurrentUserIdDep,
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> list[OrganizationResponse]:
    orgs = await org_service.list_for_user(user_id)
    return [
        OrganizationResponse(id=o.id, name=o.name, slug=o.slug, created_at=o.created_at) for o in orgs
    ]


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: uuid.UUID,
    user_id: CurrentUserIdDep,
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationResponse:
    org = await org_service.get_by_id(organization_id, user_id)
    return OrganizationResponse(id=org.id, name=org.name, slug=org.slug, created_at=org.created_at)


@router.post(
    "/{organization_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED
)
async def add_member(
    organization_id: uuid.UUID,
    payload: AddMemberRequest,
    user_id: CurrentUserIdDep,
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> MemberResponse:
    member = await org_service.add_member(organization_id, user_id, payload.user_id, payload.role)
    return MemberResponse(
        organization_id=member.organization_id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.get("/{organization_id}/members", response_model=list[MemberResponse])
async def list_members(
    organization_id: uuid.UUID,
    user_id: CurrentUserIdDep,
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> list[MemberResponse]:
    members = await org_service.list_members(organization_id, user_id)
    return [
        MemberResponse(
            organization_id=m.organization_id, user_id=m.user_id, role=m.role, joined_at=m.joined_at
        )
        for m in members
    ]
