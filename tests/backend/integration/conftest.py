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
    # Minimal secrets so auth module loads.
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("JWT_REFRESH_SECRET", "y" * 32)
    app_module = importlib.import_module("app.main")
    auth_module = importlib.import_module("app.interfaces.api.routers.auth")
    search_module = importlib.import_module("app.interfaces.api.routers.search")
    qa_module = importlib.import_module("app.interfaces.api.routers.qa")
    summary_module = importlib.import_module("app.interfaces.api.routers.summary")
    schemas = importlib.import_module("app.interfaces.api.schemas")

    fake_pool = DummyPool()
    monkeypatch.setattr(app_module.db, "init_pool", lambda: None)
    monkeypatch.setattr(app_module.db, "close_pool", lambda: None)
    monkeypatch.setattr(app_module.db, "pool", fake_pool)
    monkeypatch.setattr(app_module.db, "get_pool", lambda: fake_pool)

    dummy_user = schemas.UserPublic(
        user_id="u1",
        email="test@example.com",
        full_name=None,
        role="user",
        firm_id=None,
    )
    # Override dependencies using the original callables so auth is bypassed.
    app_module.app.dependency_overrides[auth_module.get_current_user] = (
        lambda: dummy_user
    )
    app_module.app.dependency_overrides[search_module.get_current_user] = (
        lambda: dummy_user
    )
    app_module.app.dependency_overrides[qa_module.get_current_user] = lambda: dummy_user
    app_module.app.dependency_overrides[summary_module.get_current_user] = (
        lambda: dummy_user
    )

    return {
        "app": app_module.app,
        "search": search_module,
        "qa": qa_module,
        "summary": summary_module,
        "pool": fake_pool,
    }


@pytest.fixture
def client(app_modules):
    return TestClient(app_modules["app"])
