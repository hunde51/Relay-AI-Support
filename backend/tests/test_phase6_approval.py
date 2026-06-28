import asyncio
from sqlalchemy import select


def test_approve_pending_action(client, session_factory):
    """Approving a pending action should succeed and set status to approved."""
    create = client.post("/tickets", json={"title": "ApproveTest", "message": "Help"})
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    assert resp.status_code == 200
    action_id = resp.json()["suggested_action_id"]

    resp2 = client.post(f"/ai/actions/{action_id}/approve", json={})
    assert resp2.status_code == 200
    assert resp2.json()["approval_status"] == "approved"

    actions = client.get(f"/ai/tickets/{tid}/suggested-actions").json()
    assert any(a["id"] == action_id and a["approval_status"] == "approved" for a in actions)


def test_approve_already_approved_returns_404(client, session_factory):
    """Approving an already-approved action should fail."""
    create = client.post("/tickets", json={"title": "DoubleApprove", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/approve", json={}).status_code == 200

    assert client.post(f"/ai/actions/{action_id}/approve", json={}).status_code == 404


def test_reject_pending_action(client, session_factory):
    """Rejecting a pending action should succeed and set status to rejected."""
    create = client.post("/tickets", json={"title": "RejectTest", "message": "Help"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    resp2 = client.post(f"/ai/actions/{action_id}/reject", json={})
    assert resp2.status_code == 200
    assert resp2.json()["approval_status"] == "rejected"


def test_reject_already_rejected_returns_404(client, session_factory):
    """Rejecting an already-rejected action should fail."""
    create = client.post("/tickets", json={"title": "DoubleReject", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/reject", json={}).status_code == 200
    assert client.post(f"/ai/actions/{action_id}/reject", json={}).status_code == 404


def test_execute_rejected_action_fails(client, session_factory):
    """Executing a rejected action should return an error."""
    create = client.post("/tickets", json={"title": "ExecRejected", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/reject", json={}).status_code == 200

    resp2 = client.post(f"/ai/actions/{action_id}/execute", json={})
    assert resp2.status_code == 400
    assert "rejected" in resp2.json()["detail"].lower()


def test_execute_double_fails(client, session_factory):
    """Executing an already executed action should fail."""
    create = client.post("/tickets", json={"title": "DoubleExec", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/approve", json={}).status_code == 200
    assert client.post(f"/ai/actions/{action_id}/execute", json={}).status_code == 200

    resp2 = client.post(f"/ai/actions/{action_id}/execute", json={})
    assert resp2.status_code == 400
    assert "already been executed" in resp2.json()["detail"].lower()


def test_execute_resolve_action_works(client, session_factory):
    """Executing a resolve action should actually resolve the ticket."""
    create = client.post("/tickets", json={"title": "ExecResolve", "message": "Fix it"})
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/approve", json={}).status_code == 200

    exec_resp = client.post(f"/ai/actions/{action_id}/execute", json={})
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "resolved"

    ticket = client.get(f"/tickets/{tid}").json()
    assert ticket["status"] == "resolved"


def test_suggested_actions_include_ai_run_id(client, session_factory):
    """The ticket-level suggested actions endpoint should include ai_run_id."""
    create = client.post("/tickets", json={"title": "AiRunIdTest", "message": "Test"})
    tid = create.json()["id"]

    client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})

    actions = client.get(f"/ai/tickets/{tid}/suggested-actions").json()
    assert len(actions) >= 1
    assert "ai_run_id" in actions[0]
    assert actions[0]["ai_run_id"] is not None


def test_execute_without_approval_fails(client, session_factory):
    """Executing a requires_approval=True action without approving should fail."""
    create = client.post("/tickets", json={"title": "NoApprove", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    resp2 = client.post(f"/ai/actions/{action_id}/execute", json={})
    assert resp2.status_code == 400
    assert "not approved" in resp2.json()["detail"].lower()


def test_approval_creates_audit_log(client, session_factory):
    """Approving an action should create an audit log entry."""
    create = client.post("/tickets", json={"title": "AuditApprove", "message": "Test"})
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    action_id = resp.json()["suggested_action_id"]

    assert client.post(f"/ai/actions/{action_id}/approve", json={}).status_code == 200

    async def _check():
        async with session_factory() as db:
            from app.db.models import AuditLogORM
            result = await db.execute(
                select(AuditLogORM).where(
                    AuditLogORM.resource_type == "ai_suggested_action",
                    AuditLogORM.resource_id == action_id,
                )
            )
            logs = result.scalars().all()
            assert any(log.action == "approve" for log in logs)

    asyncio.run(_check())
