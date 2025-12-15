from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.infrastructure.db import connection as db

TABLE_DDL = """
CREATE TABLE IF NOT EXISTS review_runs (
    trace_id TEXT PRIMARY KEY,
    firm_id TEXT,
    user_id TEXT,
    status TEXT,
    doc_type TEXT,
    structural_findings JSONB,
    issues JSONB,
    suggestions JSONB,
    qa_notes JSONB,
    residual_risks JSONB,
    summary JSONB,
    conflict_check JSONB,
    errors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_review_runs_firm ON review_runs(firm_id);
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
    structural_findings: Any,
    issues: Any,
    suggestions: Any,
    qa_notes: Any,
    residual_risks: Any,
    summary: Any,
    conflict_check: Any,
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
        "structural_findings": json.dumps(structural_findings)
        if structural_findings is not None
        else None,
        "issues": json.dumps(issues) if issues is not None else None,
        "suggestions": json.dumps(suggestions) if suggestions is not None else None,
        "qa_notes": json.dumps(qa_notes) if qa_notes is not None else None,
        "residual_risks": json.dumps(residual_risks)
        if residual_risks is not None
        else None,
        "summary": json.dumps(summary) if summary is not None else None,
        "conflict_check": json.dumps(conflict_check)
        if conflict_check is not None
        else None,
        "errors": json.dumps(errors) if errors is not None else None,
    }
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO review_runs (trace_id, firm_id, user_id, status, doc_type, structural_findings, issues, suggestions, qa_notes, residual_risks, summary, conflict_check, errors)
            VALUES (%(trace_id)s, %(firm_id)s, %(user_id)s, %(status)s, %(doc_type)s, %(structural_findings)s, %(issues)s, %(suggestions)s, %(qa_notes)s, %(residual_risks)s, %(summary)s, %(conflict_check)s, %(errors)s)
            ON CONFLICT (trace_id) DO UPDATE SET
                firm_id = EXCLUDED.firm_id,
                user_id = EXCLUDED.user_id,
                status = EXCLUDED.status,
                doc_type = EXCLUDED.doc_type,
                structural_findings = EXCLUDED.structural_findings,
                issues = EXCLUDED.issues,
                suggestions = EXCLUDED.suggestions,
                qa_notes = EXCLUDED.qa_notes,
                residual_risks = EXCLUDED.residual_risks,
                summary = EXCLUDED.summary,
                conflict_check = EXCLUDED.conflict_check,
                errors = EXCLUDED.errors,
                updated_at = now()
            RETURNING trace_id, firm_id, user_id, status, doc_type, structural_findings, issues, suggestions, qa_notes, residual_risks, summary, conflict_check, errors, created_at, updated_at
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
        "structural_findings": _parse(row["structural_findings"]),
        "issues": _parse(row["issues"]),
        "suggestions": _parse(row["suggestions"]),
        "qa_notes": _parse(row["qa_notes"]),
        "residual_risks": _parse(row["residual_risks"]),
        "summary": _parse(row["summary"]),
        "conflict_check": _parse(row["conflict_check"]),
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
            SELECT trace_id, firm_id, user_id, status, doc_type, structural_findings, issues, suggestions, qa_notes, residual_risks, summary, conflict_check, errors, created_at, updated_at
            FROM review_runs
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
        "structural_findings": _parse(row["structural_findings"]),
        "issues": _parse(row["issues"]),
        "suggestions": _parse(row["suggestions"]),
        "qa_notes": _parse(row["qa_notes"]),
        "residual_risks": _parse(row["residual_risks"]),
        "summary": _parse(row["summary"]),
        "conflict_check": _parse(row["conflict_check"]),
        "errors": _parse(row["errors"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
