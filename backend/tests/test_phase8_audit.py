import pytest
from sqlalchemy import select

from app.db.models import AISuggestedActionORM, AuditLogORM, UserORM
from app.db.seed import DEFAULT_ORG_ID


async def create_user(db, role: str):
    u = UserORM(organization_id=DEFAULT_ORG_ID, name=f"{role} user", email=f"{role}@example.com", role=role)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_approve_requires_role(client, session_factory):
    # create suggested action directly
    async with session_factory() as db:
        action = AISuggestedActionORM(ai_run_id="AIR-TEST", ticket_id="TID-1", action_type="resolve_ticket", payload={}, risk_level="high", requires_approval=True)
        db.add(action)
        await db.flush()
        # create two users
        agent = await create_user(db, "agent")
        admin = await create_user(db, "admin")
        await db.commit()

        # agent should not be allowed
        resp = client.post(f"/ai/actions/{action.id}/approve", json={"actor_user_id": agent.id})
        assert resp.status_code == 404

        # admin should be allowed
        resp2 = client.post(f"/ai/actions/{action.id}/approve", json={"actor_user_id": admin.id})
        assert resp2.status_code == 200

        # check audit log
        result = await db.execute(select(AuditLogORM).where(AuditLogORM.resource_id == action.id))
        logs = result.scalars().all()
        assert len(logs) >= 1
