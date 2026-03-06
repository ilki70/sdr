from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "agente_vendedor",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_track_started=True,
)
import app.workers.tasks.evaluation  # noqa: F401,E402
import app.workers.tasks.ingestion  # noqa: F401,E402
