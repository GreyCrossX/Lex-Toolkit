from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.application import ingestion_service
from app.infrastructure.db import ingestion_repository
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import UploadResponse, UploadStatus, UploadStatusResponse, UserPublic
from app.interfaces.worker.tasks import ingest_upload

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
ALLOWED_DOC_TYPES = {"statute", "jurisprudence", "contract", "policy"}


async def _handle_upload(doc_type: str, file: UploadFile) -> UploadResponse:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de documento no soportado: {doc_type}",
        )
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF.",
        )

    job = ingestion_repository.create_job(filename=file.filename or "document.pdf", content_type=file.content_type or "", doc_type=doc_type)
    ingestion_repository.update_job(job.job_id, status="uploading", message="Recibiendo archivo...", progress=5)

    try:
        saved_path = ingestion_service.save_upload(job.job_id, file)
    except ValueError as exc:
        ingestion_repository.update_job(
            job.job_id,
            status="failed",
            progress=100,
            error=str(exc),
            message="Archivo rechazado.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - runtime protection
        ingestion_repository.update_job(
            job.job_id,
            status="failed",
            progress=100,
            error=str(exc),
            message="No se pudo guardar el archivo.",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el archivo.",
        ) from exc

    ingestion_repository.update_job(
        job.job_id,
        status="uploading",
        progress=15,
        message="Archivo recibido; encolando ingesta...",
    )
    try:
        ingest_upload.delay(job.job_id, str(saved_path), doc_type)
    except Exception as exc:  # pragma: no cover - runtime protection
        ingestion_repository.update_job(
            job.job_id,
            status="failed",
            progress=100,
            error=str(exc),
            message="No se pudo encolar la ingesta.",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo encolar la ingesta.",
        ) from exc

    job = ingestion_repository.get_job(job.job_id)
    return UploadResponse(
        job_id=job.job_id if job else "",
        status=UploadStatus(job.status if job else UploadStatus.failed.value),
        message=job.message if job else "No se pudo iniciar la ingesta.",
        doc_type=doc_type,
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
) -> UploadResponse:
    # Legacy endpoint defaults to statutes/regulations.
    return await _handle_upload("statute", file)


@router.post("/ingestion/{doc_type}", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_with_doc_type(
    doc_type: str,
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
) -> UploadResponse:
    return await _handle_upload(doc_type, file)


@router.get("/upload/{job_id}", response_model=UploadStatusResponse)
def upload_status(job_id: str, current_user: UserPublic = Depends(get_current_user)) -> UploadStatusResponse:
    job = ingestion_repository.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado.",
        )

    return UploadStatusResponse(
        job_id=job.job_id,
        filename=job.filename,
        status=UploadStatus(job.status),
        progress=job.progress,
        message=job.message,
        error=job.error,
        doc_ids=job.doc_ids,
        doc_type=getattr(job, "doc_type", "statute"),
    )


@router.get("/ingestion/{job_id}", response_model=UploadStatusResponse)
def ingestion_status(job_id: str, current_user: UserPublic = Depends(get_current_user)) -> UploadStatusResponse:
    return upload_status(job_id, current_user)
