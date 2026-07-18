from appsec.infrastructure.celery_app import celery_app
from appsec.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="notifications.dispatch")
def dispatch_notification(notification_id: str) -> None:
    # Stub: future email/webhook/slack delivery integration goes here.
    logger.info("notification_dispatch_stub", notification_id=notification_id)
