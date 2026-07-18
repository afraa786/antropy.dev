import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Project:
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
