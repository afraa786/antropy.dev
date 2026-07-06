import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class ScanStarted:
    scan_job_id: uuid.UUID
    organization_id: uuid.UUID
    engines: list[str]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
