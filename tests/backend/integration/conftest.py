import importlib

import pytest

fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient


class DummyPool:
    """Minimal pool stub to avoid real DB connections in integration tests."""

    def connection(self):
        raise RuntimeError("Connection should not be used in mocked integration tests")


@pytest.fixture
def app_modules(monkeypatch):
    """
    Load app + routers with a fake pool so startup doesn't require DATABASE_URL.
    Returns modules for monkeypatching in tests.
    """
    app_module = importlib.import_module("app.main")
    search_module = importlib.import_module("app.routers.search")
    qa_module = importlib.import_module("app.routers.qa")

    fake_pool = DummyPool()
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)
    monkeypatch.setattr(app_module.db, "close_pool", lambda: None)
    monkeypatch.setattr(app_module.db, "pool", fake_pool)
    monkeypatch.setattr(app_module.db, "get_pool", lambda: fake_pool)

    return {
        "app": app_module.app,
        "search": search_module,
        "qa": qa_module,
        "pool": fake_pool,
    }


@pytest.fixture
def client(app_modules):
    return TestClient(app_modules["app"])
