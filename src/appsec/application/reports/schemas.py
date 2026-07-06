import uuid
from datetime import datetime

from pydantic import BaseModel

from appsec.domain.enums import ReportFormat, ReportStatus


class CreateReportRequest(BaseModel):
    format: ReportFormat = ReportFormat.JSON


class ReportResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    scan_job_id: uuid.UUID | None
    format: ReportFormat
    status: ReportStatus
    file_path: str | None
    generated_at: datetime | None
    created_at: datetime
