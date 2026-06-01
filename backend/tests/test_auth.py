import pytest
from app.db.models import TicketORM, UserORM
from app.db.seed import DEFAULT_ORG_ID


@pytest.mark.asyncio
async def test_auth_injection(client, session_factory):
    # create a ticket belonging to default org
    async with session_factory() as db:
        t = TicketORM(id="TKT-AUTH-1", organization_id=DEFAULT_ORG_ID, title="Test", message="msg")
        db.add(t)
        await db.flush()
        await db.commit()

    # issue a token using the auth endpoint
    resp = client.post("/auth/token", json={"user_id": "USR-TEST", "organization_id": DEFAULT_ORG_ID, "role": "agent"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # call run endpoint with Authorization header
    headers = {"Authorization": f"Bearer {token}"}
    resp2 = client.post(f"/ai/tickets/{t.id}/run", headers=headers)
    assert resp2.status_code == 200
    body = resp2.json()
    assert "run_id" in body
