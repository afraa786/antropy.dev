import uuid
from dataclasses import dataclass
from datetime import datetime

from appsec.domain.enums import VerificationMethod, VerificationStatus


@dataclass(slots=True)
class Domain:
    id: uuid.UUID
    project_id: uuid.UUID
    organization_id: uuid.UUID
    hostname: str
    verification_status: VerificationStatus
    verification_method: VerificationMethod
    verification_token: str
    verified_at: datetime | None
    created_at: datetime

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VerificationStatus.VERIFIED
