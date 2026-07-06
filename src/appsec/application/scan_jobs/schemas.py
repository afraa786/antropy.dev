import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from appsec.domain.enums import ScanStatus


class CreateScanJobRequest(BaseModel):
    domain_id: uuid.UUID
    scan_type: str = Field(default="default", max_length=64)


class ScanJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    organization_id: uuid.UUID
    domain_id: uuid.UUID
    status: ScanStatus
    scan_type: str
    created_by: uuid.UUID
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
