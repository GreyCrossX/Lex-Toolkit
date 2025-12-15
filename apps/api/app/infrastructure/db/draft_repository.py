from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.infrastructure.db import connection as db

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS draft_runs (
    trace_id TEXT PRIMARY KEY,
    firm_id TEXT,
    user_id TEXT,
    status TEXT,
    doc_type TEXT,
    plan JSONB,
    sections JSONB,
    draft TEXT,
    assumptions JSONB,
    open_questions JSONB,
    risks JSONB,
    errors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_draft_runs_firm ON draft_runs(firm_id);
"""


def ensure_table() -> None:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(TABLE_DDL)
        conn.commit()


def upsert_run(
    trace_id: str,
    *,
    firm_id: Optional[str],
    user_id: Optional[str],
    status: str,
    doc_type: str,
    plan: Any,
    sections: Any,
    draft: Optional[str],
    assumptions: Any,
    open_questions: Any,
    risks: Any,
    errors: Any,
) -> Dict[str, Any]:
    ensure_table()
    pool = db.get_pool()
    payload = {
        "trace_id": trace_id,
        "firm_id": firm_id,
        "user_id": user_id,
        "status": status,
        "doc_type": doc_type,
        "plan": json.dumps(plan) if plan is not None else None,
        "sections": json.dumps(sections) if sections is not None else None,
        "draft": draft,
        "assumptions": json.dumps(assumptions) if assumptions is not None else None,
        "open_questions": json.dumps(open_questions)
        if open_questions is not None
        else None,
        "risks": json.dumps(risks) if risks is not None else None,
        "errors": json.dumps(errors) if errors is not None else None,
    }
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO draft_runs (trace_id, firm_id, user_id, status, doc_type, plan, sections, draft, assumptions, open_questions, risks, errors)
            VALUES (%(trace_id)s, %(firm_id)s, %(user_id)s, %(status)s, %(doc_type)s, %(plan)s, %(sections)s, %(draft)s, %(assumptions)s, %(open_questions)s, %(risks)s, %(errors)s)
            ON CONFLICT (trace_id) DO UPDATE SET
                firm_id = EXCLUDED.firm_id,
                user_id = EXCLUDED.user_id,
                status = EXCLUDED.status,
                doc_type = EXCLUDED.doc_type,
                plan = EXCLUDED.plan,
                sections = EXCLUDED.sections,
                draft = EXCLUDED.draft,
                assumptions = EXCLUDED.assumptions,
                open_questions = EXCLUDED.open_questions,
                risks = EXCLUDED.risks,
                errors = EXCLUDED.errors,
                updated_at = now()
            RETURNING trace_id, firm_id, user_id, status, doc_type, plan, sections, draft, assumptions, open_questions, risks, errors, created_at, updated_at
            """,
            payload,
        )
        row = cur.fetchone()
        conn.commit()

    def _parse(val):
        if val is None:
            return None
        return val if isinstance(val, (dict, list)) else json.loads(val)

    return {
        "trace_id": row["trace_id"],
        "firm_id": row["firm_id"],
        "user_id": row["user_id"],
        "status": row["status"],
        "doc_type": row["doc_type"],
        "plan": _parse(row["plan"]),
        "sections": _parse(row["sections"]),
        "draft": row["draft"],
        "assumptions": _parse(row["assumptions"]),
        "open_questions": _parse(row["open_questions"]),
        "risks": _parse(row["risks"]),
        "errors": _parse(row["errors"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_run(trace_id: str, firm_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ensure_table()
    pool = db.get_pool()
    params = {"trace_id": trace_id}
    where = "trace_id = %(trace_id)s"
    if firm_id:
        where += " AND (firm_id IS NULL OR firm_id = %(firm_id)s)"
        params["firm_id"] = firm_id

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT trace_id, firm_id, user_id, status, doc_type, plan, sections, draft, assumptions, open_questions, risks, errors, created_at, updated_at
            FROM draft_runs
            WHERE {where}
            """,
            params,
        )
        row = cur.fetchone()

    if not row:
        return None

    def _parse(val):
        if val is None:
            return None
        return val if isinstance(val, (dict, list)) else json.loads(val)

    return {
        "trace_id": row["trace_id"],
        "firm_id": row["firm_id"],
        "user_id": row["user_id"],
        "status": row["status"],
        "doc_type": row["doc_type"],
        "plan": _parse(row["plan"]),
        "sections": _parse(row["sections"]),
        "draft": row["draft"],
        "assumptions": _parse(row["assumptions"]),
        "open_questions": _parse(row["open_questions"]),
        "risks": _parse(row["risks"]),
        "errors": _parse(row["errors"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
