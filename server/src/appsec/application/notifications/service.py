import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.notification import Notification
from appsec.domain.enums import NotificationType
from appsec.domain.exceptions import NotFoundError
from appsec.domain.repositories.notification_repository import NotificationRepository
from appsec.infrastructure.tasks.notifications import dispatch_notification


class NotificationService:
    def __init__(self, session: AsyncSession, notification_repository: NotificationRepository) -> None:
        self._session = session
        self._notifications = notification_repository

    async def create(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        payload: dict[str, Any],
    ) -> Notification:
        notification = Notification(
            id=uuid.uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            type=notification_type,
            payload=payload,
            read_at=None,
            created_at=datetime.now(UTC),
        )
        created = await self._notifications.create(notification)
        await self._session.commit()
        dispatch_notification.delay(str(created.id))
        return created

    async def list_for_user(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> list[Notification]:
        return await self._notifications.list_for_user(user_id, organization_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        updated = await self._notifications.mark_read(notification_id, user_id)
        if updated is None:
            raise NotFoundError(f"Notification {notification_id} not found")
        await self._session.commit()
        return updated
