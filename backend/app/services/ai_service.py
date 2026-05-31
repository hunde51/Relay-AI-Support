from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AIRunORM, AIStepORM, AISuggestedActionORM
from app.db.seed import DEFAULT_ORG_ID
from app.ai_engine.graph import agent_graph
from app.ai_engine.state import AgentState
from app.core.ws_manager import manager
from app.repositories import ticket_repository


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


async def run_ai_on_ticket(db: AsyncSession, ticket_id: str) -> dict:
    ticket = await ticket_repository.get_by_id(db, ticket_id)
    if not ticket:
        return {"error": "Ticket not found"}

    ai_run = AIRunORM(
        ticket_id=ticket_id,
        organization_id=DEFAULT_ORG_ID,
        status="running",
        started_at=_utc_now(),
    )
    db.add(ai_run)
    await db.flush()
    run_id = ai_run.id

    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "organization_id": DEFAULT_ORG_ID,
        "title": ticket.title,
        "message": ticket.message,
        "category": ticket.category,
        "priority": ticket.priority,
        "issue_type": "",
        "knowledge_results": [],
        "decision": "escalate",
        "response": "",
        "citations": [],
        "steps": [],
    }

    try:
        result = await agent_graph.ainvoke(initial_state)

        # Persist each step
        for step_data in result["steps"]:
            step = AIStepORM(
                ai_run_id=run_id,
                step_name=step_data["step"],
                output=step_data,
                confidence=str(step_data.get("confidence", "")),
            )
            db.add(step)

        # Determine risk level and approval requirement
        decision = result["decision"]
        confidence = result["steps"][-1].get("confidence", 0.5) if result["steps"] else 0.5
        risk_level = "high" if ticket.category in ("billing", "account") else "medium" if confidence < 0.8 else "low"
        requires_approval = risk_level in ("high", "medium") or confidence < 0.85

        # Persist suggested action
        action = AISuggestedActionORM(
            ai_run_id=run_id,
            ticket_id=ticket_id,
            action_type=decision,
            payload={"response": result["response"], "citations": result.get("citations", [])},
            risk_level=risk_level,
            requires_approval=requires_approval,
        )
        db.add(action)

        ai_run.status = "completed"
        ai_run.final_decision = decision
        ai_run.confidence = str(confidence)
        ai_run.risk_level = risk_level
        ai_run.completed_at = _utc_now()

    except Exception as e:
        ai_run.status = "failed"
        ai_run.error = str(e)
        ai_run.completed_at = _utc_now()

    await db.commit()
    await db.refresh(ai_run)

    # Notify frontend the run is done
    await manager.broadcast_ticket({
        "event": "ai_run_completed",
        "ticket_id": ticket_id,
        "run_id": run_id,
        "decision": ai_run.final_decision,
        "status": ai_run.status,
    })

    return {
        "run_id": run_id,
        "status": ai_run.status,
        "final_decision": ai_run.final_decision,
        "confidence": ai_run.confidence,
        "risk_level": ai_run.risk_level,
        "error": ai_run.error,
    }


async def get_runs_for_ticket(db: AsyncSession, ticket_id: str) -> list:
    result = await db.execute(
        select(AIRunORM)
        .where(AIRunORM.ticket_id == ticket_id)
        .order_by(AIRunORM.created_at.desc())
    )
    return result.scalars().all()


async def get_run_steps(db: AsyncSession, run_id: str) -> list:
    result = await db.execute(
        select(AIStepORM)
        .where(AIStepORM.ai_run_id == run_id)
        .order_by(AIStepORM.created_at)
    )
    return result.scalars().all()


async def get_suggested_actions(db: AsyncSession, ticket_id: str) -> list:
    result = await db.execute(
        select(AISuggestedActionORM)
        .where(AISuggestedActionORM.ticket_id == ticket_id)
        .order_by(AISuggestedActionORM.created_at.desc())
    )
    return result.scalars().all()


async def approve_action(db: AsyncSession, action_id: str) -> AISuggestedActionORM | None:
    result = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return None
    action.approval_status = "approved"
    action.approved_at = _utc_now()
    await db.commit()
    await db.refresh(action)
    return action


async def reject_action(db: AsyncSession, action_id: str) -> AISuggestedActionORM | None:
    result = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return None
    action.approval_status = "rejected"
    action.rejected_at = _utc_now()
    await db.commit()
    await db.refresh(action)
    return action
