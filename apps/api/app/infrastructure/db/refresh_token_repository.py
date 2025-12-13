from datetime import datetime
from typing import Optional

from app.core.domain.auth import RefreshToken
from app.infrastructure.db import connection as db


TABLE_CREATE = """
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    replaced_by TEXT,
    parent_id TEXT,
    reused BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_reason TEXT,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

TABLE_ALTERS = [
    "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS parent_id TEXT",
    "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS reused BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS revoked_reason TEXT",
    "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ",
]

TABLE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_parent ON refresh_tokens(parent_id)",
]


def ensure_table() -> None:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(TABLE_CREATE)
        for stmt in TABLE_ALTERS:
            cur.execute(stmt)
        for stmt in TABLE_INDEXES:
            cur.execute(stmt)
        conn.commit()


def _row_to_token(row) -> RefreshToken:
    getter = row.get if hasattr(row, "get") else lambda k: row[k]
    return RefreshToken(
        token_id=getter("token_id"),
        user_id=getter("user_id"),
        secret_hash=getter("secret_hash"),
        revoked=bool(getter("revoked")),
        replaced_by=getter("replaced_by"),
        parent_id=getter("parent_id"),
        reused=bool(getter("reused")),
        revoked_reason=getter("revoked_reason"),
        last_used_at=getter("last_used_at"),
        expires_at=getter("expires_at"),
        created_at=getter("created_at"),
    )


def create_token(
    token_id: str,
    user_id: str,
    secret_hash: str,
    expires_at: datetime,
    replaced_by: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> RefreshToken:
    ensure_table()
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (token_id, user_id, secret_hash, revoked, replaced_by, parent_id, reused, revoked_reason, last_used_at, expires_at)
            VALUES (%(token_id)s, %(user_id)s, %(secret_hash)s, FALSE, %(replaced_by)s, %(parent_id)s, FALSE, NULL, now(), %(expires_at)s)
            RETURNING token_id, user_id, secret_hash, revoked, replaced_by, parent_id, reused, revoked_reason, last_used_at, expires_at, created_at
            """,
            {
                "token_id": token_id,
                "user_id": user_id,
                "secret_hash": secret_hash,
                "replaced_by": replaced_by,
                "parent_id": parent_id,
                "expires_at": expires_at,
            },
        )
        row = cur.fetchone()
        conn.commit()
    return _row_to_token(row)


def get_token(token_id: str) -> Optional[RefreshToken]:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT token_id, user_id, secret_hash, revoked, replaced_by, parent_id, reused, revoked_reason, last_used_at, expires_at, created_at
            FROM refresh_tokens
            WHERE token_id = %(token_id)s
            """,
            {"token_id": token_id},
        )
        row = cur.fetchone()
    return _row_to_token(row) if row else None


def revoke_token(
    token_id: str,
    replaced_by: Optional[str] = None,
    reason: Optional[str] = None,
    mark_reused: bool = False,
) -> Optional[RefreshToken]:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked = TRUE,
                replaced_by = COALESCE(%(replaced_by)s, replaced_by),
                revoked_reason = COALESCE(%(reason)s, revoked_reason),
                reused = reused OR %(mark_reused)s
            WHERE token_id = %(token_id)s
            RETURNING token_id, user_id, secret_hash, revoked, replaced_by, parent_id, reused, revoked_reason, last_used_at, expires_at, created_at
            """,
            {
                "token_id": token_id,
                "replaced_by": replaced_by,
                "reason": reason,
                "mark_reused": mark_reused,
            },
        )
        row = cur.fetchone()
        conn.commit()
    return _row_to_token(row) if row else None


def touch_token(token_id: str) -> None:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET last_used_at = now()
            WHERE token_id = %(token_id)s
            """,
            {"token_id": token_id},
        )
        conn.commit()


def revoke_chain_from(
    token_id: str, reason: str = "reuse-detected", mark_reused: bool = False
) -> None:
    """
    Revoke a token and its descendants (following replaced_by chain) to mitigate token reuse.
    """
    seen = set()
    current = token_id
    while current and current not in seen:
        seen.add(current)
        record = get_token(current)
        if record is None:
            break
        revoke_token(
            record.token_id,
            replaced_by=record.replaced_by,
            reason=reason,
            mark_reused=mark_reused,
        )
        current = record.replaced_by
