import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from appsec.domain.enums import VerificationMethod, VerificationStatus


class CreateDomainRequest(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    verification_method: VerificationMethod = VerificationMethod.DNS_TXT


class DomainResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    organization_id: uuid.UUID
    hostname: str
    verification_status: VerificationStatus
    verification_method: VerificationMethod
    verification_token: str
    verified_at: datetime | None
    created_at: datetime


class VerificationInstructionsResponse(BaseModel):
    domain_id: uuid.UUID
    method: VerificationMethod
    dns_txt_record_name: str | None = None
    dns_txt_record_value: str | None = None
    http_file_url: str | None = None
    http_file_content: str | None = None
