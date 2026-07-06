import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from appsec.domain.enums import NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
