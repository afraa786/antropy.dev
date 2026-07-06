import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
