import uuid
from datetime import datetime
from typing import Optional

from app.core.domain.ingestion import IngestionJob
from app.infrastructure.db import connection as db


TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT,
    doc_type TEXT NOT NULL DEFAULT 'statute',
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    doc_ids TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);
"""


def ensure_table() -> None:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(TABLE_DDL)
        cur.execute("ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS doc_type TEXT NOT NULL DEFAULT 'statute';")
        conn.commit()


def _row_to_job(row) -> IngestionJob:
    getter = row.get if hasattr(row, "get") else lambda k: row[k]
    return IngestionJob(
        job_id=getter("job_id"),
        filename=getter("filename"),
        content_type=getter("content_type"),
        doc_type=getter("doc_type") or "statute",
        status=getter("status"),
        progress=int(getter("progress")),
        message=getter("message") or "",
        error=getter("error"),
        doc_ids=getter("doc_ids") or [],
        created_at=getter("created_at"),
        updated_at=getter("updated_at"),
    )


def create_job(filename: str, content_type: str, doc_type: str = "statute") -> IngestionJob:
    ensure_table()
    pool = db.get_pool()
    job_id = str(uuid.uuid4())
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_jobs (job_id, filename, content_type, doc_type, status, progress, message)
            VALUES (%(job_id)s, %(filename)s, %(content_type)s, %(doc_type)s, %(status)s, %(progress)s, %(message)s)
            RETURNING job_id, filename, content_type, doc_type, status, progress, message, error, doc_ids, created_at, updated_at
            """,
            {
                "job_id": job_id,
                "filename": filename,
                "content_type": content_type,
                "doc_type": doc_type,
                "status": "queued",
                "progress": 0,
                "message": "Trabajo en cola para ingesta.",
            },
        )
        row = cur.fetchone()
        conn.commit()
    return _row_to_job(row)


def update_job(job_id: str, **kwargs) -> Optional[IngestionJob]:
    pool = db.get_pool()
    allowed_keys = {"status", "progress", "message", "error", "doc_ids", "filename", "content_type", "doc_type"}
    set_clauses = []
    params = {"job_id": job_id}
    for key, value in kwargs.items():
        if key not in allowed_keys:
            continue
        set_clauses.append(f"{key} = %({key})s")
        params[key] = value

    if not set_clauses:
        return get_job(job_id)

    set_clauses.append("updated_at = now()")
    set_sql = ", ".join(set_clauses)

    query = f"""
        UPDATE ingestion_jobs
        SET {set_sql}
        WHERE job_id = %(job_id)s
        RETURNING job_id, filename, content_type, doc_type, status, progress, message, error, doc_ids, created_at, updated_at
    """

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
    return _row_to_job(row) if row else None


def get_job(job_id: str) -> Optional[IngestionJob]:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT job_id, filename, content_type, doc_type, status, progress, message, error, doc_ids, created_at, updated_at
            FROM ingestion_jobs
            WHERE job_id = %(job_id)s
            """,
            {"job_id": job_id},
        )
        row = cur.fetchone()
    return _row_to_job(row) if row else None
