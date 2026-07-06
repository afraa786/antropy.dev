import uuid
from typing import Protocol

from appsec.domain.entities.notification import Notification


class NotificationRepository(Protocol):
    async def create(self, notification: Notification) -> Notification: ...

    async def list_for_user(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[Notification]: ...

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None: ...
