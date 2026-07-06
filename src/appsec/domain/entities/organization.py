import uuid
from dataclasses import dataclass
from datetime import datetime

from appsec.domain.enums import OrganizationRole


@dataclass(slots=True)
class Organization:
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


@dataclass(slots=True)
class OrganizationMember:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrganizationRole
    joined_at: datetime
