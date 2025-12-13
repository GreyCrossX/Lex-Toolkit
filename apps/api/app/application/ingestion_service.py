import asyncio
from pathlib import Path
from typing import Callable, Optional

from fastapi import UploadFile

from app.infrastructure.db import connection as db
from app.infrastructure.db import ingestion_repository as ingest_repo
from app.infrastructure.ingestion.pipeline import ingest_pdf

UPLOAD_ROOT = Path("data/uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def save_upload(job_id: str, upload: UploadFile) -> Path:
    target_dir = UPLOAD_ROOT / job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(upload.filename or "document.pdf").name
    dest_path = target_dir / safe_name

    bytes_written = 0
    upload.file.seek(0)
    with dest_path.open("wb") as buffer:
        while True:
            chunk = upload.file.read(1024 * 512)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                dest_path.unlink(missing_ok=True)
                raise ValueError(f"El archivo excede el limite de {MAX_UPLOAD_MB}MB.")
            buffer.write(chunk)

    return dest_path


async def process_job(
    job_id: str,
    file_path: Path,
    ingest_callback: Optional[Callable[[Path], object]] = None,
) -> None:
    ingest_repo.update_job(
        job_id,
        status="processing",
        progress=25,
        message="Procesando archivo y preparando ingesta.",
    )

    try:
        pool = db.get_pool()

        if ingest_callback:
            ingest_repo.update_job(
                job_id, message="Ejecutando pipeline de ingesta...", progress=50
            )
            await ingest_callback(file_path)
            doc_ids = [file_path.stem]
        else:
            ingest_repo.update_job(
                job_id, message="Extrayendo y embebiendo texto...", progress=55
            )
            doc_id, chunk_count = await asyncio.wait_for(
                asyncio.to_thread(ingest_pdf, pool, file_path, file_path.stem),
                timeout=20,
            )
            ingest_repo.update_job(
                job_id,
                message=f"Ingesta completada ({chunk_count} chunks).",
                progress=90,
            )
            doc_ids = [doc_id]
        ingest_repo.update_job(
            job_id,
            status="completed",
            progress=100,
            doc_ids=doc_ids,
            message="Documento ingestada.",
        )
    except Exception as exc:  # pragma: no cover - runtime protection
        ingest_repo.update_job(
            job_id,
            status="failed",
            progress=100,
            error=str(exc),
            message=f"Ingesta fallida: {exc}",
        )
