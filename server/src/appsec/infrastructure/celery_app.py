from celery import Celery

from appsec.config import get_settings

settings = get_settings()

celery_app = Celery(
    "appsec",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "appsec.infrastructure.tasks.domain_verification",
        "appsec.infrastructure.tasks.notifications",
        "appsec.infrastructure.tasks.scan_execution",
        "appsec.infrastructure.tasks.urlscan_execution",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
