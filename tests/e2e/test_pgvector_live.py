"""
Live pgvector smoke tests.

Requires:
  - Environment variable RUN_PGVECTOR_TESTS=1
  - DATABASE_URL pointing at a pgvector instance with a populated `legal_chunks` table.

These tests do not mutate data; they only read and assert ordering/limits.
"""

import importlib
import os

import pytest

RUN_PGVECTOR = os.environ.get("RUN_PGVECTOR_TESTS") == "1"
DATABASE_URL = os.environ.get("DATABASE_URL")

if not RUN_PGVECTOR:
    pytest.skip(
        "Set RUN_PGVECTOR_TESTS=1 to run live pgvector tests", allow_module_level=True
    )

if not DATABASE_URL:
    pytest.skip(
        "DATABASE_URL is required for live pgvector tests", allow_module_level=True
    )

fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient

from app.application.search_service import run_search  # noqa: E402
from app.infrastructure.db import connection as db  # noqa: E402
from app.interfaces.api.schemas import SearchRequest  # noqa: E402


def ensure_pool():
    db.DATABASE_URL = DATABASE_URL
    try:
        db.init_pool()
    except RuntimeError:
        # Pool already initialized.
        pass
    return db.get_pool()


def get_vector_dims(pool):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT vector_dims(embedding) AS dims FROM legal_chunks LIMIT 1")
        row = cur.fetchone()
        if not row or not row["dims"]:
            pytest.skip(
                "legal_chunks is empty; seed data required for live pgvector tests"
            )
        return int(row["dims"])


def test_run_search_live_sorted_results():
    pool = ensure_pool()
    dims = get_vector_dims(pool)
    # Use a zero vector of the correct dimension; rely on DB ordering by distance.
    req = SearchRequest(embedding=[0.0] * dims, limit=5, max_distance=5.0)

    results = run_search(pool, req)
    if not results:
        pytest.skip("No search results returned; ensure seed data is present")

    distances = [r.distance for r in results]
    assert distances == sorted(distances)
    assert len(results) <= 5


def test_qa_live_respects_max_distance_and_sort(monkeypatch):
    app_module = importlib.import_module("app.main")
    qa_module = importlib.import_module("app.interfaces.api.routers.qa")
    pool = ensure_pool()
    dims = get_vector_dims(pool)

    # Bypass real embeddings; use zero vector of correct dimension.
    monkeypatch.setattr(qa_module.llm, "embed_text", lambda _: [0.0] * dims)
    monkeypatch.setattr(app_module.db, "pool", pool)
    monkeypatch.setattr(app_module.db, "get_pool", lambda: pool)
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)

    client = TestClient(app_module.app)
    resp = client.post("/qa", json={"query": "hola", "top_k": 3, "max_distance": 5.0})
    assert resp.status_code == 200
    data = resp.json()
    if not data["citations"]:
        pytest.skip("No citations returned; ensure seed data is present")

    distances = [c["distance"] for c in data["citations"]]
    assert distances == sorted(distances)
    assert len(distances) <= 3
