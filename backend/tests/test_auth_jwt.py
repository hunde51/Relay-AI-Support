import pytest
from importlib import util

pytestmark = pytest.mark.asyncio

HAS_PYJWT = util.find_spec("jwt") is not None


def test_issue_token_format(client):
    resp = client.post("/auth/token", json={"user_id": "U1", "organization_id": "ORG1", "role": "agent"})
    assert resp.status_code == 200
    tok = resp.json()["access_token"]
    if HAS_PYJWT:
        assert tok.count(".") == 2  # JWT has 3 parts
    else:
        # base64 fallback
        assert "=" in tok or len(tok) > 10
