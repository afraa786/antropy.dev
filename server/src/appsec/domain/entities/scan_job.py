import uuid
from dataclasses import dataclass
from datetime import datetime

from appsec.domain.enums import ScanStatus


@dataclass(slots=True)
class ScanJob:
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
