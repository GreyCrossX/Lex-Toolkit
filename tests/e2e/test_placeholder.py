import pytest


@pytest.mark.xfail(
    reason="E2E requiere stack vivo (docker compose) + datos seed", strict=False
)
def test_e2e_placeholder():
    assert True
