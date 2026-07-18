import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from appsec.domain.enums import NotificationType


@dataclass(slots=True)
class Notification:
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    payload: dict[str, Any] = field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
