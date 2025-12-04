import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)
WORKER_CONCURRENCY = int(os.environ.get("CELERY_CONCURRENCY", "1"))
TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "120"))
TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "110"))

celery_app = Celery(
    "app",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    # Keep ingestion jobs on a dedicated queue for now.
    task_routes={"app.interfaces.worker.ingest_upload": {"queue": "ingest"}},
    # One-at-a-time ingestion to avoid heavy memory usage in prefork workers.
    worker_concurrency=WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=TASK_TIME_LIMIT,
    task_soft_time_limit=TASK_SOFT_TIME_LIMIT,
)

celery_app.autodiscover_tasks(["app.interfaces.worker"])


@celery_app.task
def ping() -> str:
    return "pong"
