from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AIRunORM, AIStepORM, AISuggestedActionORM
from app.db.seed import DEFAULT_ORG_ID
from app.ai_engine.graph import agent_graph
from app.ai_engine.state import AgentState
from app.repositories import ticket_repository


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


async def run_ai_on_ticket(db: AsyncSession, ticket_id: str) -> dict:
    ticket = await ticket_repository.get_by_id(db, ticket_id)
    if not ticket:
        return {"error": "Ticket not found"}

    # Create the AI run record upfront so nodes can reference it
    ai_run = AIRunORM(
        ticket_id=ticket_id,
        organization_id=DEFAULT_ORG_ID,
        status="running",
        started_at=_utc_now(),
    )
    db.add(ai_run)
    await db.flush()

    initial_state: AgentState = {
        # Required inputs
        "ticket_id": ticket_id,
        "organization_id": DEFAULT_ORG_ID,
        "ai_run_id": ai_run.id,
        "db": db,
        # Ticket fields (refreshed by load_ticket_context node)
        "title": ticket.title,
        "message": ticket.message,
        "category": ticket.category,
        "priority": ticket.priority,
        "customer_id": ticket.customer_id,
        "assignee_id": ticket.assignee_id,
        "ticket_context_loaded": False,
        # Defaults — filled by nodes
        "classified_category": ticket.category,
        "intent": "",
        "confidence": 0.5,
        "sentiment": "neutral",
        "urgency": "medium",
        "sla_risk": False,
        "knowledge_results": [],
        "has_relevant_knowledge": False,
        "repeat_issue": False,
        "recent_escalations": 0,
        "decision": "escalate",
        "decision_confidence": 0.5,
        "risk_level": "medium",
        "decision_reason": "",
        "response": "",
        "citations": [],
        "validation_valid": True,
        "validation_issues": [],
        "escalation_team": "",
        "escalation_note": "",
        "suggested_action_id": "",
        "requires_approval": True,
        "steps": [],
    }

    try:
        await agent_graph.ainvoke(initial_state)
        # persist_ai_run node already committed; refresh to get final state
        await db.refresh(ai_run)
    except Exception as e:
        ai_run.status = "failed"
        ai_run.error = str(e)
        ai_run.completed_at = _utc_now()
        await db.commit()
        await db.refresh(ai_run)

    return {
        "run_id": ai_run.id,
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
