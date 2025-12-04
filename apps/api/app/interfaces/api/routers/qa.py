from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg_pool import ConnectionPool

from app.application.search_service import run_search
from app.infrastructure.db import connection as db
from app.infrastructure.llm import openai_client as llm
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import QARequest, QAResponse, QACitation, SearchRequest, UserPublic

router = APIRouter()


@router.post("/qa", response_model=QAResponse)
def qa(
    req: QARequest,
    pool: ConnectionPool = Depends(db.get_pool),
    _: UserPublic = Depends(get_current_user),
) -> QAResponse:
    if not req.query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text is required.",
        )

    try:
        query_embedding = llm.embed_text(req.query)
    except Exception as exc:  # pragma: no cover - runtime protection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to embed query: {exc}",
        ) from exc

    search_req = SearchRequest(
        embedding=query_embedding,
        limit=req.top_k,
        doc_ids=req.doc_ids,
        jurisdictions=req.jurisdictions,
        sections=req.sections,
        max_distance=req.max_distance,
    )

    try:
        results = run_search(pool, search_req)
    except Exception as exc:  # pragma: no cover - runtime protection
        print(f"[qa] search error: {type(exc)} {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc

    if not results:
        return QAResponse(answer="No relevant context found.", citations=[])

    context_chunks: List[str] = []
    citations: List[QACitation] = []
    for res in results:
        snippet = (res.content or "")[:400]
        context_chunks.append(f"[chunk_id={res.chunk_id}] {snippet}")
        citations.append(
            QACitation(
                chunk_id=res.chunk_id,
                doc_id=res.doc_id,
                section=res.section,
                jurisdiction=res.jurisdiction,
                metadata=res.metadata,
                content=snippet,
                distance=res.distance,
            )
        )

    try:
        answer = llm.generate_answer(req.query, context_chunks, max_tokens=req.max_tokens)
    except Exception as exc:  # pragma: no cover - runtime protection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {exc}",
        ) from exc

    return QAResponse(answer=answer, citations=citations)
