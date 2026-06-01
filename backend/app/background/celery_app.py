from celery import Celery
from app.core.config import settings

broker = settings.REDIS_URL or "redis://redis:6379/0"
celery_app = Celery("relayai", broker=broker)

@celery_app.task(name="app.background.sample_task")
def sample_task(data):
    # placeholder task
    print("Running sample task with:", data)
    return {"status": "ok", "data": data}
