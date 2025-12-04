from fastapi import APIRouter, Depends, HTTPException, status
from psycopg_pool import ConnectionPool

from app.application.search_service import run_search
from app.infrastructure.db import connection as db
from app.infrastructure.llm import openai_client as llm
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import SearchRequest, SearchResponse, UserPublic

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(
    req: SearchRequest,
    pool: ConnectionPool = Depends(db.get_pool),
    _: UserPublic = Depends(get_current_user),
) -> SearchResponse:
    embedding = req.embedding
    if embedding is None:
        if not req.query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either query text or embedding.",
            )
        try:
            embedding = llm.embed_text(req.query)
        except Exception as exc:  # pragma: no cover - runtime protection
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to embed query: {exc}",
            ) from exc

    req.embedding = embedding

    try:
        results = run_search(pool, req)
    except Exception as exc:  # pragma: no cover - runtime protection
        # Log the exception type/value to help debugging.
        print(f"[search] error: {type(exc)} {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc
    return SearchResponse(results=results)
