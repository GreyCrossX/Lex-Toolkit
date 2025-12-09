from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.infrastructure.db import connection as db

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS research_runs (
    trace_id TEXT PRIMARY KEY,
    firm_id TEXT,
    user_id TEXT,
    status TEXT,
    issues JSONB,
    research_plan JSONB,
    queries JSONB,
    briefing JSONB,
    errors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_research_runs_firm ON research_runs(firm_id);
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
    issues: Any,
    research_plan: Any,
    queries: Any,
    briefing: Any,
    errors: Any,
) -> Dict[str, Any]:
    ensure_table()
    pool = db.get_pool()
    payload = {
        "trace_id": trace_id,
        "firm_id": firm_id,
        "user_id": user_id,
        "status": status,
        "issues": json.dumps(issues) if issues is not None else None,
        "research_plan": json.dumps(research_plan) if research_plan is not None else None,
        "queries": json.dumps(queries) if queries is not None else None,
        "briefing": json.dumps(briefing) if briefing is not None else None,
        "errors": json.dumps(errors) if errors is not None else None,
    }
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO research_runs (trace_id, firm_id, user_id, status, issues, research_plan, queries, briefing, errors)
            VALUES (%(trace_id)s, %(firm_id)s, %(user_id)s, %(status)s, %(issues)s, %(research_plan)s, %(queries)s, %(briefing)s, %(errors)s)
            ON CONFLICT (trace_id) DO UPDATE SET
                firm_id = EXCLUDED.firm_id,
                user_id = EXCLUDED.user_id,
                status = EXCLUDED.status,
                issues = EXCLUDED.issues,
                research_plan = EXCLUDED.research_plan,
                queries = EXCLUDED.queries,
                briefing = EXCLUDED.briefing,
                errors = EXCLUDED.errors,
                updated_at = now()
            RETURNING trace_id, firm_id, user_id, status, issues, research_plan, queries, briefing, errors, created_at, updated_at
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
        "issues": _parse(row["issues"]),
        "research_plan": _parse(row["research_plan"]),
        "queries": _parse(row["queries"]),
        "briefing": _parse(row["briefing"]),
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
            SELECT trace_id, firm_id, user_id, status, issues, research_plan, queries, briefing, errors, created_at, updated_at
            FROM research_runs
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
        "issues": _parse(row["issues"]),
        "research_plan": _parse(row["research_plan"]),
        "queries": _parse(row["queries"]),
        "briefing": _parse(row["briefing"]),
        "errors": _parse(row["errors"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
