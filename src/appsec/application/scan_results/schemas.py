import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ScanResultResponse(BaseModel):
    id: uuid.UUID
    scan_job_id: uuid.UUID
    organization_id: uuid.UUID
    summary: dict[str, Any]
    severity_counts: dict[str, int]
    created_at: datetime
