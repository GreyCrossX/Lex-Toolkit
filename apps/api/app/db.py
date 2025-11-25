import os
from typing import Callable, Optional

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


DATABASE_URL = os.environ.get("DATABASE_URL")

pool: Optional[ConnectionPool] = None


def _configure_connection(conn) -> None:
    register_vector(conn)


def init_pool() -> None:
    global pool
    if pool is not None:
        return
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    # Small pool for now; adjust once the API grows.
    pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=5,
        max_idle=5,
        timeout=10,
        configure=_configure_connection,
        # Dict rows keep the response payload simple.
        kwargs={"row_factory": dict_row},
    )


def close_pool() -> None:
    global pool
    if pool is not None:
        pool.close()
        pool = None


def get_pool() -> ConnectionPool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool
