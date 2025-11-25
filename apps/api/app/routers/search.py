from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import sql
from psycopg_pool import ConnectionPool

from app import db
from app.schemas import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


def build_where_clauses(
    req: SearchRequest, params: Dict[str, object], distance_sql: str
) -> Tuple[List[str], Dict[str, object]]:
    clauses: List[str] = ["embedding IS NOT NULL"]

    if req.doc_ids:
        clauses.append("doc_id = ANY(%(doc_ids)s)")
        params["doc_ids"] = req.doc_ids

    if req.jurisdictions:
        clauses.append("jurisdiction = ANY(%(jurisdictions)s)")
        params["jurisdictions"] = [j.lower() for j in req.jurisdictions]

    if req.sections:
        clauses.append("section = ANY(%(sections)s)")
        params["sections"] = req.sections

    if req.max_distance is not None:
        clauses.append(f"{distance_sql} <= %(max_distance)s")
        params["max_distance"] = req.max_distance

    return clauses, params


@router.post("/search", response_model=SearchResponse)
def search(
    req: SearchRequest,
    pool: ConnectionPool = Depends(db.get_pool),
) -> SearchResponse:
    embedding_str = "[" + ",".join(str(x) for x in req.embedding) + "]"
    params: Dict[str, object] = {
        "embedding": embedding_str,
        "limit": req.limit,
    }

    distance_sql = "embedding <-> %(embedding)s::vector"
    clauses, params = build_where_clauses(req, params, distance_sql)
    where_sql = " AND ".join(clauses)

    query = sql.SQL(
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
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover - runtime protection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc

    results = [
        SearchResult(
            chunk_id=row[0],
            doc_id=row[1],
            section=row[2],
            jurisdiction=row[3],
            metadata=row[4] or {},
            content=row[5],
            distance=float(row[6]),
        )
        for row in rows
    ]
    return SearchResponse(results=results)
