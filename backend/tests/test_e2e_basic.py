import pytest
from app.db.seed import DEFAULT_ORG_ID


@pytest.mark.asyncio
async def test_create_ticket_and_run_ai(client, session_factory):
    # create ticket
    payload = {"title": "E2E Ticket", "message": "Please help"}
    resp = client.post("/tickets", json=payload)
    assert resp.status_code in (200, 201)
    ticket = resp.json()

    # get token
    tkn = client.post("/auth/token", json={"user_id": "e2e-user", "organization_id": DEFAULT_ORG_ID, "role": "agent"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tkn}"}

    # run AI
    resp2 = client.post(f"/ai/tickets/{ticket['id']}/run", headers=headers)
    assert resp2.status_code == 200
    body = resp2.json()
    assert "run_id" in body
