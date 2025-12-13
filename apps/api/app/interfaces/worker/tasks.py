import logging
from pathlib import Path
from typing import Tuple

from celery.exceptions import SoftTimeLimitExceeded

from app.infrastructure.db import connection as db
from app.infrastructure.db import ingestion_repository
from app.infrastructure.ingestion.pipeline import ingest_pdf
from app.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


def _ensure_db() -> None:
    try:
        db.get_pool()
    except RuntimeError:
        db.init_pool()


@celery_app.task(name="app.interfaces.worker.ingest_upload")
def ingest_upload(
    job_id: str, file_path: str, doc_type: str = "statute"
) -> Tuple[str, int]:
    """
    Celery task to ingest an uploaded document.
    """
    logger.info("Starting ingest job %s for %s", job_id, file_path)
    _ensure_db()
    ingestion_repository.update_job(
        job_id,
        status="processing",
        progress=25,
        message="Worker: procesando archivo...",
    )
    path = Path(file_path)

    try:
        pool = db.get_pool()
        doc_id, chunk_count = ingest_pdf(pool, path, path.stem, doc_type=doc_type)
        ingestion_repository.update_job(
            job_id,
            status="completed",
            progress=100,
            doc_ids=[doc_id],
            message=f"Ingesta completada ({chunk_count} chunks).",
        )
        logger.info("Ingest job %s completed (%s chunks)", job_id, chunk_count)
        return doc_id, chunk_count
    except SoftTimeLimitExceeded:
        ingestion_repository.update_job(
            job_id,
            status="failed",
            progress=100,
            error="Tiempo limite excedido en worker.",
            message="Ingesta fallida por timeout.",
        )
        logger.exception("Ingest job %s timed out", job_id)
        raise
    except Exception as exc:
        ingestion_repository.update_job(
            job_id,
            status="failed",
            progress=100,
            error=str(exc),
            message=f"Ingesta fallida: {exc}",
        )
        logger.exception("Ingest job %s failed", job_id)
        raise
