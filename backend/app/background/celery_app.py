from celery import Celery

from app.core.config import settings


broker_url = settings.REDIS_URL or "redis://redis:6379/0"

celery_app = Celery(
    "relayai",
    broker=broker_url,
    backend=broker_url,
    include=["app.background.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
