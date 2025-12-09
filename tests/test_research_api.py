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
    research_router = importlib.import_module("app.interfaces.api.routers.research")

    # No-op DB/table setup for tests.
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)
    monkeypatch.setattr(app_module.ingestion_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.user_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.refresh_token_repository, "ensure_table", lambda: None)
    monkeypatch.setattr(app_module.research_repository, "ensure_table", lambda: None)

    # Dummy auth.
    class DummyUser:
        user_id = "user-1"
        email = "u@example.com"
        firm_id = "firm-1"

    # In-memory store.
    store = {}

    def fake_run(prompt, firm_id=None, user_id=None, max_search_steps=None, trace_id=None):
        tid = trace_id or "trace-1"
        data = {
            "trace_id": tid,
            "status": "answered",
            "issues": [{"id": "I1", "question": prompt}],
            "research_plan": [],
            "queries": [],
            "briefing": {"overview": "ok"},
        }
        store[tid] = data
        return data

    def fake_upsert(trace_id, **kwargs):
        payload = {
            "trace_id": trace_id,
            "status": kwargs.get("status"),
            "issues": kwargs.get("issues"),
            "research_plan": kwargs.get("research_plan"),
            "queries": kwargs.get("queries"),
            "briefing": kwargs.get("briefing"),
            "errors": kwargs.get("errors"),
            "firm_id": kwargs.get("firm_id"),
            "user_id": kwargs.get("user_id"),
        }
        store[trace_id] = payload
        return payload

    def fake_get(trace_id, firm_id=None):
        return store.get(trace_id)

    monkeypatch.setattr(research_router, "run_research", fake_run)
    monkeypatch.setattr(research_router.research_repository, "upsert_run", fake_upsert)
    monkeypatch.setattr(research_router.research_repository, "get_run", fake_get)
    monkeypatch.setattr(research_router.rate_limit, "enforce", lambda *args, **kwargs: None)

    client = TestClient(app_module.app)
    client.app.dependency_overrides[research_router.get_current_user] = lambda: DummyUser()
    return client, store


def test_research_run_and_get(monkeypatch):
    client, store = make_client(monkeypatch)

    resp = client.post("/research/run", json={"prompt": "Investigar despido injustificado"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"]
    assert data["status"] == "answered"
    assert data["issues"][0]["question"]

    trace_id = data["trace_id"]
    assert trace_id in store

    resp_get = client.get(f"/research/{trace_id}")
    assert resp_get.status_code == 200
    fetched = resp_get.json()
    assert fetched["trace_id"] == trace_id
    assert fetched["issues"]


def test_research_run_rate_limited(monkeypatch):
    client, _ = make_client(monkeypatch)
    research_router = importlib.import_module("app.interfaces.api.routers.research")
    from app.infrastructure.security.rate_limit import RateLimitExceeded

    def raise_rl(*args, **kwargs):
        raise RateLimitExceeded()

    monkeypatch.setattr(research_router.rate_limit, "enforce", raise_rl)

    resp = client.post("/research/run", json={"prompt": "hola mundo legal"})
    assert resp.status_code == 429


def test_research_run_stream(monkeypatch):
    client, store = make_client(monkeypatch)

    research_router = importlib.import_module("app.interfaces.api.routers.research")

    class FakeGraph:
        def compile(self):
            return self

        def stream(self, initial_state, stream_mode="updates"):
            yield {"issues": [{"id": "I1", "question": "streamed"}]}
            yield {"research_plan": [{"id": "P1", "issue_id": "I1", "description": "plan"}]}
            yield {"status": "answered", "briefing": {"overview": "done"}}

    monkeypatch.setattr(research_router, "build_research_graph", lambda: FakeGraph())

    with client.stream("POST", "/research/run/stream", json={"prompt": "streaming test"}) as resp:
        assert resp.status_code == 200
        lines = list(resp.iter_lines())

    assert len(lines) >= 2
    start_evt = json.loads(lines[0])
    done_evt = json.loads(lines[-1])
    assert start_evt["type"] == "start"
    assert done_evt["type"] == "done"
    trace_id = done_evt["trace_id"]
    assert trace_id in store
