from typing import Dict, List, Tuple

from psycopg import sql
from psycopg_pool import ConnectionPool

from app.schemas import SearchRequest, SearchResult


def _build_where_clauses(
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


def run_search(
    pool: ConnectionPool,
    req: SearchRequest,
) -> List[SearchResult]:
    # Build pgvector literal as text, then cast to vector in SQL.
    embedding_literal = "[" + ",".join(str(x) for x in req.embedding) + "]"
    params: Dict[str, object] = {
        "embedding": embedding_literal,
        "limit": req.limit,
    }

    distance_sql = "embedding <-> %(embedding)s::vector"
    clauses, params = _build_where_clauses(req, params, distance_sql)
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

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    results: List[SearchResult] = []
    for row in rows:
        # Support dict rows (default) or tuple rows if row_factory changes.
        getter = row.get if hasattr(row, "get") else lambda k: row[k]
        results.append(
            SearchResult(
                chunk_id=getter("chunk_id") if "chunk_id" in row else row[0],
                doc_id=getter("doc_id") if "doc_id" in row else row[1],
                section=getter("section") if "section" in row else row[2],
                jurisdiction=getter("jurisdiction") if "jurisdiction" in row else row[3],
                metadata=getter("metadata") if "metadata" in row else row[4] or {},
                content=getter("content") if "content" in row else row[5],
                distance=float(getter("distance") if "distance" in row else row[6]),
            )
        )
    return results
