import importlib
import json

import pytest

fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient

NEW_PRIV = """-----BEGIN PRIVATE KEY-----
MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAL372MQLXYNKNGS3
vCyt/s2/ixKfMqNy2hACXwt4MKmkPodRd7GDHZgw7M+whe9ZYqJRQmuIVzLY4+6k
6mhCNq6e9Kdl3YfUuwP5jwXt/4uWdV5zz84viEOQq8cOJEX6fLLkvkUaYrDGRzjQ
6VQQ+fyuCty6O2/Iz+jcvx6QFE0JAgMBAAECgYBGqb3ebTvC8X67V3uuQqlbbbsU
mhIDqVxiR/+CDJpM/sIjIrIaXGJNkSUDuuyWMfD13rONu5BzYSimQsDNNpOPij5h
VDXrTuTwRdJ8YXjBt2qp6cSKu/RVsEoKmWwNibSG72sy4QExOwWHUM9yqsaMioBO
eXEGl5oMam6ylb5S4QJBAPppvpsaw5VzH994M3CoXpemrypqX4793DZx31B/9Bad
sIMCnEfVP8ZfwEsLbbQpqkWws/5cMgNJy1p1qKQKsGsCQQDCOPSG94jL7Dy1/vAw
qbsmgF3pYYUjcvIZnrIEe3+ec4t0yFJopfNvEmED/UkkrXZFmit88tEhhA6BwAo/
4IVbAkADRFPnRB8fGQRmbvQE2T16rwMEA6VBgVBZKX0nWLP/g4kk/Gi7iy2s0dz5
XanNuulsxVRj0iIY5uKPSI+trDIHAkBW6wg7knGM2Sb+R54UGRFhFJdyhyr/B0Tj
RErkiKQ/M/RYCgIfRQ0hSvdRwrtGB77jPTBzFXOT7TZUyK2Nkpv7AkBmbsqWLqsP
Loc4uck/2C8BXvaCvMQ7wsN1WdMOkwxZFYLkMVR+qIoRkJvaolr+z6enFme5z28U
mIviQua2Skeu
-----END PRIVATE KEY-----"""

NEW_PUB = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC9+9jEC12DSjRkt7wsrf7Nv4sS
nzKjctoQAl8LeDCppD6HUXexgx2YMOzPsIXvWWKiUUJriFcy2OPupOpoQjaunvSn
Zd2H1LsD+Y8F7f+LlnVec8/OL4hDkKvHDiRF+nyy5L5FGmKwxkc40OlUEPn8rgrc
ujtvyM/o3L8ekBRNCQIDAQAB
-----END PUBLIC KEY-----"""


def test_jwks_route_serves_public_keys(monkeypatch):
    monkeypatch.setenv("JWT_PRIVATE_KEY", NEW_PRIV)
    monkeypatch.setenv("JWT_PRIVATE_KEY_ID", "kid-new")
    monkeypatch.setenv("JWT_PUBLIC_KEYS", json.dumps({"kid-new": NEW_PUB}))
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    auth_module = importlib.reload(
        importlib.import_module("app.interfaces.api.routers.auth")
    )
    app = fastapi.FastAPI()
    app.include_router(auth_module.router)

    client = TestClient(app)
    resp = client.get("/auth/jwks")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert any(k.get("kid") == "kid-new" for k in data["keys"])
