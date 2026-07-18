import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from appsec.domain.enums import OrganizationRole


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: OrganizationRole = OrganizationRole.MEMBER


class MemberResponse(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrganizationRole
    joined_at: datetime
