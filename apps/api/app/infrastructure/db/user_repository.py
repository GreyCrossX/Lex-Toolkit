import uuid
from typing import Optional

from app.core.domain.user import User
from app.infrastructure.db import connection as db


def ensure_table() -> None:
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                firm_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.commit()


def create_user(
    email: str,
    password_hash: str,
    full_name: Optional[str],
    role: str = "user",
    firm_id: Optional[str] = None,
) -> str:
    ensure_table()
    pool = db.get_pool()
    user_id = str(uuid.uuid4())
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id, email, password_hash, full_name, role, firm_id)
            VALUES (%(user_id)s, %(email)s, %(password_hash)s, %(full_name)s, %(role)s, %(firm_id)s)
            """,
            {
                "user_id": user_id,
                "email": email.lower(),
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
                "firm_id": firm_id,
            },
        )
        conn.commit()
    return user_id


def _row_to_user(row) -> User:
    getter = row.get if hasattr(row, "get") else lambda k: row[k]
    return User(
        user_id=getter("user_id"),
        email=getter("email"),
        password_hash=getter("password_hash"),
        full_name=getter("full_name"),
        role=getter("role"),
        firm_id=getter("firm_id"),
    )


def get_user_by_email(email: str) -> Optional[User]:
    ensure_table()
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, email, password_hash, full_name, role, firm_id
            FROM users
            WHERE email = %(email)s
            """,
            {"email": email.lower()},
        )
        row = cur.fetchone()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: str) -> Optional[User]:
    ensure_table()
    pool = db.get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, email, password_hash, full_name, role, firm_id
            FROM users
            WHERE user_id = %(user_id)s
            """,
            {"user_id": user_id},
        )
        row = cur.fetchone()
    return _row_to_user(row) if row else None
