from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool
from langchain_openai import OpenAIEmbeddings
from pgvector.psycopg import register_vector
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger(__name__)


_pool: Optional[ConnectionPool] = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set; cannot connect to pgvector")

    _pool = ConnectionPool(
        conninfo=db_url,
        min_size=1,
        max_size=4,
        max_idle=4,
        timeout=10,
        configure=register_vector,
        kwargs={"row_factory": dict_row},
    )
    return _pool


def _embed_query(text: str) -> List[float]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot embed query")
    model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    embedder = OpenAIEmbeddings(model=model, api_key=api_key)
    return embedder.embed_query(text)


class PGVectorInspectorArgs(BaseModel):
    query: str = Field(..., description="Text to embed and search over legal_chunks")
    top_k: int = Field(5, ge=1, le=50, description="Number of rows to return (1-50)")
    doc_ids: Optional[List[str]] = Field(None, description="Filter by doc_id list")
    jurisdictions: Optional[List[str]] = Field(
        None, description="Filter by jurisdiction list (lowercased)"
    )
    sections: Optional[List[str]] = Field(None, description="Filter by section list")
    max_distance: Optional[float] = Field(None, description="Optional distance cap")
    embedding: Optional[List[float]] = Field(
        None, description="Precomputed embedding; skips embed step if set"
    )
    firm_id: Optional[str] = Field(
        None, description="Optional tenant/firm filter (matches metadata->>'firm_id')"
    )

    @field_validator("jurisdictions", mode="before")
    def _lower_juris(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        return [j.lower() for j in v]

    @field_validator("embedding")
    def _validate_dim(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("embedding cannot be empty")
        return v


def _run_pgvector_inspector(
    query: str,
    top_k: int = 5,
    doc_ids: Optional[List[str]] = None,
    jurisdictions: Optional[List[str]] = None,
    sections: Optional[List[str]] = None,
    max_distance: Optional[float] = None,
    embedding: Optional[List[float]] = None,
    firm_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        emb = embedding or _embed_query(query)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("pgvector_inspector embedding fallback: %s", exc)
        return {
            "count": 1,
            "results": [
                {
                    "chunk_id": "stub",
                    "doc_id": "stub",
                    "section": "",
                    "jurisdiction": "",
                    "metadata": {},
                    "content": f"(offline stub) {query[:200]}",
                    "distance": 0.0,
                }
            ],
        }

    embedding_literal = "[" + ",".join(str(x) for x in emb) + "]"
    params: Dict[str, Any] = {"embedding": embedding_literal, "limit": top_k}

    distance_sql = "embedding <-> %(embedding)s::vector"
    clauses = ["embedding IS NOT NULL"]

    if doc_ids:
        clauses.append("doc_id = ANY(%(doc_ids)s)")
        params["doc_ids"] = doc_ids
    if jurisdictions:
        clauses.append("jurisdiction = ANY(%(jurisdictions)s)")
        params["jurisdictions"] = jurisdictions
    if sections:
        clauses.append("section = ANY(%(sections)s)")
        params["sections"] = sections
    if max_distance is not None:
        clauses.append(f"{distance_sql} <= %(max_distance)s")
        params["max_distance"] = max_distance
    if firm_id:
        clauses.append("metadata ->> 'firm_id' = %(firm_id)s")
        params["firm_id"] = firm_id

    where_sql = " AND ".join(clauses)
    query_sql = sql.SQL(
        """
        SELECT
            chunk_id,
            doc_id,
            section,
            jurisdiction,
            metadata,
            content,
            {distance} AS distance
        FROM legal_chunks
        WHERE {where}
        ORDER BY {distance}
        LIMIT %(limit)s
        """
    ).format(where=sql.SQL(where_sql), distance=sql.SQL(distance_sql))

    try:
        with _get_pool().connection() as conn, conn.cursor() as cur:
            cur.execute(query_sql, params)
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("pgvector_inspector query failed: %s", exc)
        return {
            "count": 1,
            "results": [
                {
                    "chunk_id": "stub",
                    "doc_id": "stub",
                    "section": "",
                    "jurisdiction": "",
                    "metadata": {},
                    "content": f"(offline stub) {query[:200]}",
                    "distance": 0.0,
                }
            ],
        }

    results: List[Dict[str, Any]] = []
    for row in rows:
        getter = row.get if hasattr(row, "get") else lambda k: row[k]
        results.append(
            {
                "chunk_id": getter("chunk_id") if "chunk_id" in row else row[0],
                "doc_id": getter("doc_id") if "doc_id" in row else row[1],
                "section": getter("section") if "section" in row else row[2],
                "jurisdiction": getter("jurisdiction")
                if "jurisdiction" in row
                else row[3],
                "metadata": getter("metadata") if "metadata" in row else row[4],
                "content": getter("content") if "content" in row else row[5],
                "distance": float(getter("distance") if "distance" in row else row[6]),
            }
        )

    return {
        "count": len(results),
        "results": results,
    }


pgvector_inspector_tool = StructuredTool.from_function(
    name="pgvector_inspector",
    description="Inspect the legal_chunks pgvector table using a semantic query and optional filters.",
    func=_run_pgvector_inspector,
    args_schema=PGVectorInspectorArgs,
)


__all__ = ["pgvector_inspector_tool", "PGVectorInspectorArgs"]
