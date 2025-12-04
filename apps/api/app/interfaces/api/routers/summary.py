import json
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from psycopg_pool import ConnectionPool

from app.application import summary_service
from app.infrastructure.db import connection as db
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import (
    MultiSummaryRequest,
    SummaryRequest,
    SummaryResponse,
    SummaryStreamEvent,
    UserPublic,
)

router = APIRouter()


def _ndjson_stream(events: Iterable[SummaryStreamEvent]) -> Iterable[str]:
    for event in events:
        data = event.data
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        yield json.dumps({"type": event.type, "data": data}) + "\n"


@router.post("/summary", response_model=SummaryResponse)
@router.post("/summary/document", response_model=SummaryResponse)
def summarize_document(
    req: SummaryRequest,
    pool: ConnectionPool = Depends(db.get_pool),
    _: UserPublic = Depends(get_current_user),
):
    if req.stream:
        events = summary_service.stream_summary_document(pool, req)
        return StreamingResponse(_ndjson_stream(events), media_type="application/x-ndjson")
    try:
        return summary_service.summarize_document(pool, req)
    except Exception as exc:  # pragma: no cover - runtime protection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary failed: {exc}",
        ) from exc


@router.post("/summary/multi", response_model=SummaryResponse)
def summarize_multi(
    req: MultiSummaryRequest,
    pool: ConnectionPool = Depends(db.get_pool),
    _: UserPublic = Depends(get_current_user),
):
    if req.stream:
        events = summary_service.stream_summary_multi(pool, req)
        return StreamingResponse(_ndjson_stream(events), media_type="application/x-ndjson")
    try:
        return summary_service.summarize_multi(pool, req)
    except Exception as exc:  # pragma: no cover - runtime protection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-summary failed: {exc}",
        ) from exc


@router.get("/summary/health")
def summary_health() -> dict:
    """
    Lightweight liveness probe for summary routes.
    """
    return {"status": "ok"}
