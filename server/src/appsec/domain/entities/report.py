import uuid
from dataclasses import dataclass
from datetime import datetime

from appsec.domain.enums import ReportFormat, ReportStatus


@dataclass(slots=True)
class Report:
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    scan_job_id: uuid.UUID | None
    format: ReportFormat
    status: ReportStatus
    file_path: str | None
    generated_at: datetime | None
    created_at: datetime
