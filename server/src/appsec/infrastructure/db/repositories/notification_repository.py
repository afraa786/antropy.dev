import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.notification import Notification
from appsec.infrastructure.db.models.notification import NotificationModel


def _to_entity(model: NotificationModel) -> Notification:
    return Notification(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        type=model.type,
        payload=model.payload,
        read_at=model.read_at,
        created_at=model.created_at,
    )


class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        model = NotificationModel(
            id=notification.id,
            organization_id=notification.organization_id,
            user_id=notification.user_id,
            type=notification.type,
            payload=notification.payload,
            read_at=notification.read_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_user(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> list[Notification]:
        result = await self._session.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == user_id,
                NotificationModel.organization_id == organization_id,
            )
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        model = await self._session.get(NotificationModel, notification_id)
        if model is None or model.user_id != user_id:
            return None
        model.read_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
