import uuid
from typing import Literal

from pydantic import BaseModel, Field

from appsec.domain.enums import ScanStatus


class QuickScanRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    target_type: Literal["domain", "repo"] = "domain"
    scan_type: str = Field(default="default", max_length=64)
    # Only honored when ALLOW_DEMO_VERIFICATION_SKIP=true; otherwise rejected.
    skip_verification: bool = False


class QuickScanResponse(BaseModel):
    scan_job_id: uuid.UUID
    status: ScanStatus
