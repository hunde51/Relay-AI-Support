import asyncio
from sqlalchemy import select


def test_invoke_get_ticket_persists_call(client, session_factory):
    # Create a ticket via API
    create = client.post("/tickets", json={"title": "ToolTest", "message": "Please help"})
    assert create.status_code == 201
    tid = create.json()["id"]

    # Invoke the read tool via API
    resp = client.post(f"/ai/tools/get_ticket/invoke", json={"ticket_id": tid})
    assert resp.status_code == 200
    data = resp.json()
    assert "ticket" in data and data["ticket"]["id"] == tid

    async def _check():
        async with session_factory() as db:
            from app.db.models import AIToolCallORM
            result = await db.execute(select(AIToolCallORM).where(AIToolCallORM.tool_name == "get_ticket"))
            calls = result.scalars().all()
            assert len(calls) >= 1
            call = calls[-1]
            assert call.status == "completed"
            assert call.result and "ticket" in call.result

    asyncio.run(_check())


def test_invoke_controlled_tool_creates_suggested_action(client, session_factory):
    create = client.post("/tickets", json={"title": "ResolveTest", "message": "Please resolve"})
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = client.post(f"/ai/tools/resolve_ticket/invoke", json={"ticket_id": tid})
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_action_id" in data
    suggested_id = data["suggested_action_id"]

    async def _check():
        async with session_factory() as db:
            from app.db.models import AIToolCallORM, AISuggestedActionORM
            res = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == suggested_id))
            action = res.scalar_one_or_none()
            assert action is not None

            result = await db.execute(select(AIToolCallORM).where(AIToolCallORM.tool_name == "resolve_ticket"))
            calls = result.scalars().all()
            assert len(calls) >= 1
            call = calls[-1]
            assert call.status == "suggested"
            assert call.result and call.result.get("suggested_action_id") == suggested_id

    asyncio.run(_check())
