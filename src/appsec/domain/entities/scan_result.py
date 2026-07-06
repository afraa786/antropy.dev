import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ScanResult:
    id: uuid.UUID
    scan_job_id: uuid.UUID
    organization_id: uuid.UUID
    summary: dict[str, Any] = field(default_factory=dict)
    severity_counts: dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
