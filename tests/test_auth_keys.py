import importlib
import json
import os

import pytest

OLD_PRIV = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMfoz8k9ba9if2jL
GQ/DA/eolPRb0m5xRW6Lv/XR/7NpWjmpEpvvxlmusSuMwf3un5ryng7xgxx3KDkQ
WOyt8XnrxcnFBXK+1HUM//GhC5hZKIcXHmfJhk/Q/QUEvFaWaKQKHuGdgASRP/vN
Ssxn07ATAWNh0xs7CGzisQ7z2AyLAgMBAAECgYBFCDEQlgTVZpcGsfOijL5G/FEL
nNWqy7SlOt773RuGcd/1P1wsuvzspTWLC11F+evljthj4qRa5Q7fvbRnbp2O1sgT
/vKzUPxki1AVF09+2OxS+xBMXbKpX8kpUReUnqXKm0UMmDTLMhYw4bX3iHPzVJ2u
znA5K1Flh2w0SgY5wQJBAPV9GS6qaSULXi5dVA9yDJnZl/iCboTXS/qQ4bsxyFFB
H8QcgyqPpTwuaJr6nDR9T3CPoy8taZ4wZND3rroRHKsCQQDQeBm+G+/Hd2CapLzR
sqJJhtaxWCSAovHBjqNV1qSY5zSgJYFay4CXN2QeEQ3AQXygCOVVX96pc0RF9y/9
NQ+hAkEA8sm2jiCbvLdxfglviZcSP1akpnLZOyhzTGzd03V42GPANwS79Ov8T3jW
m/AfbQpB9uEYUyBmxLy3+LP9aqhh4QJAd4OjHn5dpPknhQDUz1Od/pEzHFDv/F9u
Qg1ITrnTe2Vxoi5eTnNEsWysFSCpxYLFs+nlsGBaAsN2bLYd6Qg2gQJBAOXPJUpk
EgAIMXtQ1H7D8t41eo/iYY2mevpX8VBIRCWPBr38p4R5NNHI7bv+9pRmLaOz287r
M61i/F2YBW5Wwlk=
-----END PRIVATE KEY-----"""

OLD_PUB = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDH6M/JPW2vYn9oyxkPwwP3qJT0
W9JucUVui7/10f+zaVo5qRKb78ZZrrErjMH97p+a8p4O8YMcdyg5EFjsrfF568XJ
xQVyvtR1DP/xoQuYWSiHFx5nyYZP0P0FBLxWlmikCh7hnYAEkT/7zUrMZ9OwEwFj
YdMbOwhs4rEO89gMiwIDAQAB
-----END PUBLIC KEY-----"""

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


def _reload_auth(monkeypatch, priv: str, kid: str, pub_map: dict):
    monkeypatch.setenv("JWT_PRIVATE_KEY", priv)
    monkeypatch.setenv("JWT_PRIVATE_KEY_ID", kid)
    monkeypatch.setenv("JWT_PUBLIC_KEYS", json.dumps(pub_map))
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    # Reload module with new env.
    return importlib.reload(importlib.import_module("app.infrastructure.security.auth"))


def test_rs256_rotation_keeps_old_tokens_valid(monkeypatch):
    auth = _reload_auth(monkeypatch, OLD_PRIV, "kid-old", {"kid-old": OLD_PUB, "kid-new": NEW_PUB})
    token_old = auth.create_access_token("u1", "u@example.com", "user")
    assert auth.decode_token(token_old)["sub"] == "u1"

    auth = _reload_auth(monkeypatch, NEW_PRIV, "kid-new", {"kid-old": OLD_PUB, "kid-new": NEW_PUB})
    token_new = auth.create_access_token("u1", "u@example.com", "user")
    assert auth.decode_token(token_new)["sub"] == "u1"

    # Old token should still validate via published public key map.
    assert auth.decode_token(token_old)["sub"] == "u1"
