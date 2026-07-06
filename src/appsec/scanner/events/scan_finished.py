import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class ScanFinished:
    scan_job_id: uuid.UUID
    organization_id: uuid.UUID
    engines: list[str]
    finding_count: int
    severity_counts: dict[str, int]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
