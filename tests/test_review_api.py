import importlib

import pytest

fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient


def make_client(monkeypatch):
    # Ensure JWT config is present before importing app.main.
    import os

    os.environ.setdefault("JWT_SECRET", "testsecret" * 4)
    os.environ.setdefault("JWT_AUDIENCE", "lex-web")
    os.environ.setdefault("JWT_ISSUER", "legalscraper-api")

    app_module = importlib.import_module("app.main")
    review_router = importlib.import_module("app.interfaces.api.routers.review")

    # No-op DB/table setup for tests.
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)
    monkeypatch.setattr(app_module.ingestion_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.user_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(
        app_module.refresh_token_repository, "ensure_table", lambda: None
    )
    monkeypatch.setattr(app_module.research_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.draft_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.review_repository, "ensure_table", lambda: None)

    # Dummy auth.
    class DummyUser:
        user_id = "user-1"
        email = "u@example.com"
        firm_id = "firm-1"

    store = {}

    def fake_run(payload, firm_id=None, user_id=None, trace_id=None):
        tid = trace_id or "trace-review-1"
        data = {
            "trace_id": tid,
            "status": "answered",
            "doc_type": payload.get("doc_type", "doc"),
            "structural_findings": [
                {"issue": "Falta conclusiones", "severity": "medium"}
            ],
            "issues": [
                {
                    "category": "clarity_style",
                    "description": "Frases largas",
                    "severity": "low",
                }
            ],
            "suggestions": [{"suggestion": "Simplificar párrafo 2"}],
            "qa_notes": [],
            "residual_risks": [],
        }
        store[tid] = data
        return data

    def fake_upsert(trace_id, **kwargs):
        payload = {"trace_id": trace_id, **kwargs}
        store[trace_id] = payload
        return payload

    def fake_get(trace_id, firm_id=None):
        return store.get(trace_id)

    monkeypatch.setattr(review_router, "run_review", fake_run)
    monkeypatch.setattr(review_router.review_repository, "upsert_run", fake_upsert)
    monkeypatch.setattr(review_router.review_repository, "get_run", fake_get)
    monkeypatch.setattr(
        review_router.rate_limit, "enforce", lambda *args, **kwargs: None
    )

    client = TestClient(app_module.app)
    client.app.dependency_overrides[review_router.get_current_user] = (
        lambda: DummyUser()
    )
    return client, store


def test_review_run_and_get(monkeypatch):
    client, store = make_client(monkeypatch)

    payload = {
        "doc_type": "contrato",
        "objective": "Revisar riesgos",
        "audience": "cliente",
        "text": "Texto de prueba",
    }
    resp = client.post("/review/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"]
    assert data["structural_findings"]
    trace_id = data["trace_id"]
    assert trace_id in store

    resp_get = client.get(f"/review/{trace_id}")
    assert resp_get.status_code == 200
    fetched = resp_get.json()
    assert fetched["trace_id"] == trace_id
