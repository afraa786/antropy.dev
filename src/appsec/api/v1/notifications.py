import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_notification_service
from appsec.application.notifications.schemas import NotificationResponse
from appsec.application.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_response(notification) -> NotificationResponse:  # noqa: ANN001
    return NotificationResponse(
        id=notification.id,
        organization_id=notification.organization_id,
        user_id=notification.user_id,
        type=notification.type,
        payload=notification.payload,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[NotificationResponse]:
    notifications = await notification_service.list_for_user(user_id, organization_id)
    return [_to_response(n) for n in notifications]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user_id: CurrentUserIdDep,
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    notification = await notification_service.mark_read(notification_id, user_id)
    return _to_response(notification)
