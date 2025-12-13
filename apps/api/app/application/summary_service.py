from typing import Generator, List, Tuple

from psycopg_pool import ConnectionPool

from app.application.search_service import run_search
from app.infrastructure.llm import openai_client as llm
from app.interfaces.api.schemas import (
    MultiSummaryRequest,
    SearchRequest,
    SummaryCitation,
    SummaryRequest,
    SummaryResponse,
    SummaryStreamEvent,
)


def _build_citations(results) -> Tuple[List[SummaryCitation], List[str]]:
    citations: List[SummaryCitation] = []
    context_chunks: List[str] = []
    for res in results:
        snippet = (res.content or "")[:500]
        context_chunks.append(f"[{res.chunk_id}] {snippet}")
        citations.append(
            SummaryCitation(
                chunk_id=res.chunk_id,
                doc_id=res.doc_id,
                section=res.section,
                jurisdiction=res.jurisdiction,
                metadata=res.metadata,
                content=snippet,
                distance=res.distance,
            )
        )
    return citations, context_chunks


def _retrieve_grounded_context(
    pool: ConnectionPool, query_text: str, doc_ids: List[str], top_k: int
) -> Tuple[List[SummaryCitation], List[str]]:
    """
    Option B (grounded): embed the query_text and retrieve top_k chunks, scoped to doc_ids when provided.
    Falls back to empty retrieval if embeddings are unavailable.
    """
    try:
        embedding = llm.embed_text(query_text)
    except Exception:
        return [], []

    search_req = SearchRequest(
        query=query_text,
        embedding=embedding,
        limit=top_k,
        doc_ids=doc_ids or None,
    )
    results = run_search(pool, search_req)
    return _build_citations(results)


def summarize_document(
    pool: ConnectionPool,
    req: SummaryRequest,
) -> SummaryResponse:
    # Ground on retrieved chunks using the provided text as the query (Option B).
    query_text = req.text or "Summarize document"
    citations, context_chunks = _retrieve_grounded_context(
        pool, query_text, req.doc_ids or [], req.top_k
    )
    summary = llm.summarize_text(query_text, context_chunks, max_tokens=req.max_tokens)
    return SummaryResponse(
        summary=summary,
        citations=citations,
        model=getattr(llm, "OPENAI_MODEL", None),
        chunks_used=len(context_chunks),
    )


def stream_summary_document(
    pool: ConnectionPool,
    req: SummaryRequest,
) -> Generator[SummaryStreamEvent, None, None]:
    query_text = req.text or "Summarize document"
    citations, context_chunks = _retrieve_grounded_context(
        pool, query_text, req.doc_ids or [], req.top_k
    )
    for citation in citations:
        yield SummaryStreamEvent(type="citation", data=citation)
    for chunk in llm.stream_summary_text(
        query_text, context_chunks, max_tokens=req.max_tokens
    ):
        yield SummaryStreamEvent(type="summary_chunk", data=chunk)
    yield SummaryStreamEvent(
        type="done",
        data={
            "model": getattr(llm, "OPENAI_MODEL", None),
            "chunks_used": len(context_chunks),
        },
    )


def summarize_multi(
    pool: ConnectionPool,
    req: MultiSummaryRequest,
) -> SummaryResponse:
    # Use concatenated texts (if any) as the query for grounding; fallback to doc_ids-only.
    combined_text = "\n\n".join(req.texts or [])
    query_text = combined_text if combined_text else "Summarize multiple documents"
    # Increase retrieval budget slightly for multi-doc to cover more context.
    retrieval_limit = min(req.top_k * max(1, len(req.doc_ids or [])), 50)
    citations, context_chunks = _retrieve_grounded_context(
        pool, query_text, req.doc_ids or [], retrieval_limit
    )
    summary = llm.summarize_text(query_text, context_chunks, max_tokens=req.max_tokens)
    return SummaryResponse(
        summary=summary,
        citations=citations,
        model=getattr(llm, "OPENAI_MODEL", None),
        chunks_used=len(context_chunks),
    )


def stream_summary_multi(
    pool: ConnectionPool,
    req: MultiSummaryRequest,
) -> Generator[SummaryStreamEvent, None, None]:
    combined_text = "\n\n".join(req.texts or [])
    query_text = combined_text if combined_text else "Summarize multiple documents"
    retrieval_limit = min(req.top_k * max(1, len(req.doc_ids or [])), 50)
    citations, context_chunks = _retrieve_grounded_context(
        pool, query_text, req.doc_ids or [], retrieval_limit
    )
    for citation in citations:
        yield SummaryStreamEvent(type="citation", data=citation)
    for chunk in llm.stream_summary_text(
        query_text, context_chunks, max_tokens=req.max_tokens
    ):
        yield SummaryStreamEvent(type="summary_chunk", data=chunk)
    yield SummaryStreamEvent(
        type="done",
        data={
            "model": getattr(llm, "OPENAI_MODEL", None),
            "chunks_used": len(context_chunks),
        },
    )
