import importlib
import json

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
    drafting_router = importlib.import_module("app.interfaces.api.routers.drafting")

    # No-op DB/table setup for tests.
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)
    monkeypatch.setattr(app_module.ingestion_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.user_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.refresh_token_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.research_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.draft_repository, "ensure_table", lambda: None)

    # Dummy auth.
    class DummyUser:
        user_id = "user-1"
        email = "u@example.com"
        firm_id = "firm-1"

    store = {}

    def fake_run(payload, firm_id=None, user_id=None, trace_id=None):
        tid = trace_id or "trace-draft-1"
        data = {
            "trace_id": tid,
            "status": "answered",
            "doc_type": payload.get("doc_type", "doc"),
            "draft": "draft text",
            "draft_sections": [{"title": "Intro", "content": "Hola"}],
            "review": {"assumptions": [], "open_questions": [], "risks": []},
        }
        store[tid] = data
        return data

    def fake_upsert(trace_id, **kwargs):
        payload = {"trace_id": trace_id, **kwargs}
        store[trace_id] = payload
        return payload

    def fake_get(trace_id, firm_id=None):
        return store.get(trace_id)

    monkeypatch.setattr(drafting_router, "run_draft", fake_run)
    monkeypatch.setattr(drafting_router.draft_repository, "upsert_run", fake_upsert)
    monkeypatch.setattr(drafting_router.draft_repository, "get_run", fake_get)
    monkeypatch.setattr(drafting_router.rate_limit, "enforce", lambda *args, **kwargs: None)

    client = TestClient(app_module.app)
    client.app.dependency_overrides[drafting_router.get_current_user] = lambda: DummyUser()
    return client, store


def test_draft_run_and_get(monkeypatch):
    client, store = make_client(monkeypatch)

    payload = {
        "doc_type": "carta",
        "objective": "exigir pago",
        "audience": "contraparte",
        "tone": "formal",
        "context": "incumplimiento de pago",
        "facts": ["Contrato firmado", "Pago atrasado"],
        "requirements": [{"label": "Monto", "value": "$50,000"}],
        "constraints": ["No ceder indemnidad total"],
    }
    resp = client.post("/draft/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"]
    assert data["draft"]
    trace_id = data["trace_id"]
    assert trace_id in store

    resp_get = client.get(f"/draft/{trace_id}")
    assert resp_get.status_code == 200
    fetched = resp_get.json()
    assert fetched["trace_id"] == trace_id
    assert fetched["doc_type"] == "carta"
