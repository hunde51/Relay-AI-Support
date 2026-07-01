from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AIRunORM, AIStepORM, AISuggestedActionORM, AuditLogORM, UserORM, TicketORM
from app.ai_engine.graph import agent_graph
from app.ai_engine.state import AgentState
from app.repositories import ticket_repository
from app.db.models import OrganizationSettingsORM
from app.core.config import settings
from app.core.ws_manager import manager
from app.schemas.ticket import MessageCreate
from app.services import ticket_service


def _utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def _build_initial_state(ticket, ai_run) -> AgentState:
    return {
        # Required inputs
        "ticket_id": ticket.id,
        "organization_id": ticket.organization_id or "",
        "ai_run_id": ai_run.id,
        "db": None,  # injected per execution path
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


async def process_ai_run(db: AsyncSession, ai_run_id: str) -> dict:
    result = await db.execute(select(AIRunORM).where(AIRunORM.id == ai_run_id))
    ai_run = result.scalar_one_or_none()
    if not ai_run:
        return {"error": "AI run not found"}

    ticket = await ticket_repository.get_by_id(db, ai_run.ticket_id)
    if not ticket:
        ai_run.status = "failed"
        ai_run.error = "Ticket not found"
        ai_run.completed_at = _utc_now()
        await db.commit()
        return {"error": "Ticket not found"}

    # Respect organization-level AI enablement (feature flag)
    if ticket.organization_id:
        res = await db.execute(select(OrganizationSettingsORM).where(OrganizationSettingsORM.organization_id == ticket.organization_id))
        org_settings = res.scalar_one_or_none()
        if org_settings and not org_settings.ai_enabled:
            ai_run.status = "failed"
            ai_run.error = "AI disabled for organization"
            ai_run.completed_at = _utc_now()
            await db.commit()
            return {"error": "AI disabled for organization"}

    ai_run.status = "running"
    if not ai_run.started_at:
        ai_run.started_at = _utc_now()
    await db.commit()

    from app.core.metrics import ai_runs_total, ai_runs_active
    from app.services.usage_service import increment_ai_runs as _increment_ai_runs
    ai_runs_active.inc()

    initial_state = _build_initial_state(ticket, ai_run)
    initial_state["db"] = db

    try:
        await agent_graph.ainvoke(initial_state)
        # persist_ai_run node already committed; refresh to get final state
        await db.refresh(ai_run)
        ai_runs_total.labels(status="success").inc()
        org_id = ai_run.organization_id or ticket.organization_id
        if org_id:
            await _increment_ai_runs(
                db,
                organization_id=org_id,
                prompt_tokens=ai_run.prompt_tokens or 0,
                completion_tokens=ai_run.completion_tokens or 0,
                model=ai_run.model_name or "gemini-1.5-flash",
                resource_id=ai_run.id,
            )
    except Exception as e:
        ai_run.status = "failed"
        ai_run.error = str(e)
        ai_run.completed_at = _utc_now()
        await db.commit()
        await db.refresh(ai_run)
        ai_runs_total.labels(status="failed").inc()
    finally:
        ai_runs_active.dec()

    return {
        "run_id": ai_run.id,
        "status": ai_run.status,
        "final_decision": ai_run.final_decision,
        "confidence": ai_run.confidence,
        "risk_level": ai_run.risk_level,
        "error": ai_run.error,
    }


async def run_ai_on_ticket(db: AsyncSession, ticket_id: str) -> dict:
    ticket = await ticket_repository.get_by_id(db, ticket_id)
    if not ticket:
        return {"error": "Ticket not found"}

    ai_run = AIRunORM(
        ticket_id=ticket_id,
        organization_id=ticket.organization_id,
        status="queued" if settings.REDIS_URL else "running",
        started_at=_utc_now() if not settings.REDIS_URL else None,
        model_name="gemini-1.5-flash",
    )
    db.add(ai_run)
    await db.commit()
    await db.refresh(ai_run)

    if settings.REDIS_URL:
        from app.background.tasks import process_ai_run_task

        try:
            process_ai_run_task.delay(ai_run.id)
            return {
                "run_id": ai_run.id,
                "status": ai_run.status,
                "final_decision": ai_run.final_decision,
                "confidence": ai_run.confidence,
                "risk_level": ai_run.risk_level,
                "error": ai_run.error,
                "task_queued": True,
            }
        except Exception:
            ai_run.status = "running"
            if not ai_run.started_at:
                ai_run.started_at = _utc_now()
            await db.commit()
            return await process_ai_run(db, ai_run.id)

    return await process_ai_run(db, ai_run.id)


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


async def get_suggested_actions_for_run(db: AsyncSession, run_id: str) -> list:
    result = await db.execute(
        select(AISuggestedActionORM)
        .where(AISuggestedActionORM.ai_run_id == run_id)
        .order_by(AISuggestedActionORM.created_at.desc())
    )
    return result.scalars().all()


async def _get_action_org_id(db: AsyncSession, action: AISuggestedActionORM) -> str | None:
    """Load organisation_id from the action's ai_run or ticket."""
    if action.ai_run_id:
        r = await db.execute(select(AIRunORM).where(AIRunORM.id == action.ai_run_id))
        run = r.scalar_one_or_none()
        if run and run.organization_id:
            return run.organization_id
    t = await db.get(TicketORM, action.ticket_id)
    return t.organization_id if t else None


async def approve_action(db: AsyncSession, action_id: str, actor_user_id: str | None = None) -> AISuggestedActionORM | None:
    result = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return None
    if action.approval_status != "pending":
        return None  # can only approve pending actions

    if actor_user_id:
        u = await db.execute(select(UserORM).where(UserORM.id == actor_user_id))
        user = u.scalar_one_or_none()
        if not user or user.role not in ("admin", "manager"):
            return None

    action.approval_status = "approved"
    action.approved_by_user_id = actor_user_id
    action.approved_at = _utc_now()
    await db.flush()

    org_id = await _get_action_org_id(db, action)
    audit = AuditLogORM(
        organization_id=org_id,
        actor_type="user",
        actor_user_id=actor_user_id,
        action="approve",
        resource_type="ai_suggested_action",
        resource_id=action.id,
        metadata_json={
            "action_type": action.action_type,
            "ticket_id": action.ticket_id,
            "ai_run_id": action.ai_run_id,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)

    await manager.broadcast_ticket({
        "event": "ai_action_approved",
        "ticket_id": action.ticket_id,
        "action_id": action.id,
        "approval_status": action.approval_status,
    })
    return action


async def reject_action(db: AsyncSession, action_id: str, actor_user_id: str | None = None) -> AISuggestedActionORM | None:
    result = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return None
    if action.approval_status != "pending":
        return None  # can only reject pending actions

    if actor_user_id:
        u = await db.execute(select(UserORM).where(UserORM.id == actor_user_id))
        user = u.scalar_one_or_none()
        if not user or user.role not in ("admin", "manager"):
            return None

    action.approval_status = "rejected"
    action.rejected_by_user_id = actor_user_id
    action.rejected_at = _utc_now()
    await db.flush()

    org_id = await _get_action_org_id(db, action)
    audit = AuditLogORM(
        organization_id=org_id,
        actor_type="user",
        actor_user_id=actor_user_id,
        action="reject",
        resource_type="ai_suggested_action",
        resource_id=action.id,
        metadata_json={
            "action_type": action.action_type,
            "ticket_id": action.ticket_id,
            "ai_run_id": action.ai_run_id,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)

    await manager.broadcast_ticket({
        "event": "ai_action_rejected",
        "ticket_id": action.ticket_id,
        "action_id": action.id,
        "approval_status": action.approval_status,
    })
    return action


async def execute_suggested_action(db: AsyncSession, action_id: str, executor_user_id: str | None = None) -> dict:
    result = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return {"error": "Action not found"}

    if action.approval_status == "rejected":
        return {"error": "Action was rejected and cannot be executed"}
    if action.approval_status == "executed":
        return {"error": "Action has already been executed"}
    if action.requires_approval and action.approval_status != "approved":
        return {"error": "Action not approved"}
    if action.approval_status not in ("pending", "approved"):
        return {"error": f"Action in state '{action.approval_status}' cannot be executed"}

    if executor_user_id:
        u = await db.execute(select(UserORM).where(UserORM.id == executor_user_id))
        user = u.scalar_one_or_none()
        if not user or user.role not in ("admin", "manager"):
            return {"error": "unauthorized"}

    org_id = await _get_action_org_id(db, action)
    payload = action.payload or {}
    ticket_id = action.ticket_id

    audit_attempt = AuditLogORM(
        organization_id=org_id,
        actor_type="user",
        actor_user_id=executor_user_id,
        action="execute_attempt",
        resource_type="ai_suggested_action",
        resource_id=action.id,
        metadata_json={
            "action_type": action.action_type,
            "ticket_id": ticket_id,
            "ai_run_id": action.ai_run_id,
        },
    )
    db.add(audit_attempt)
    await db.flush()

    try:
        res = await _perform_action(db, action, executor_user_id)

        action.approval_status = "executed"
        action.approved_by_user_id = executor_user_id
        action.approved_at = _utc_now()
        await db.flush()

        audit_success = AuditLogORM(
            organization_id=org_id,
            actor_type="user",
            actor_user_id=executor_user_id,
            action="execute",
            resource_type="ai_suggested_action",
            resource_id=action.id,
            metadata_json={
                "action_type": action.action_type,
                "ticket_id": ticket_id,
                "ai_run_id": action.ai_run_id,
                "result": res,
            },
        )
        db.add(audit_success)
        await db.commit()

        await manager.broadcast_ticket({
            "event": "ai_action_executed",
            "ticket_id": ticket_id,
            "action_id": action.id,
            "approval_status": "executed",
        })
        return res
    except Exception as e:
        await db.rollback()

        error_audit = AuditLogORM(
            organization_id=org_id,
            actor_type="user",
            actor_user_id=executor_user_id,
            action="execute_failed",
            resource_type="ai_suggested_action",
            resource_id=action.id,
            metadata_json={
                "action_type": action.action_type,
                "ticket_id": ticket_id,
                "ai_run_id": action.ai_run_id,
                "error": str(e),
            },
        )
        db.add(error_audit)
        await db.commit()
        return {"error": str(e)}


AGENT_ACTION_TO_TOOL = {
    "resolve": "resolve_ticket",
    "draft_only": "send_customer_reply",
    "ask_customer": "send_customer_reply",
}


async def _perform_action(db: AsyncSession, action: AISuggestedActionORM, executor_user_id: str | None = None) -> dict:
    """Execute the real action, then return a result dict."""
    action_type = action.action_type
    payload = action.payload or {}
    ticket_id = action.ticket_id
    response_text = payload.get("response", "")
    citations = payload.get("citations", [])

    # Map agent decision names to tool names
    tool_name = AGENT_ACTION_TO_TOOL.get(action_type, action_type)

    # ── Resolve ticket ─────────────────────────────────────────────────────
    if tool_name == "resolve_ticket":
        ticket = await ticket_service.resolve_ticket(db, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        if response_text:
            await ticket_service.add_message(
                db, ticket_id,
                MessageCreate(body=response_text, is_internal=False, sender_type="agent"),
            )
        return {"ticket_id": ticket_id, "status": "resolved", "action": "resolve"}

    # ── Send customer reply (draft_only / ask_customer) ────────────────────
    if tool_name == "send_customer_reply":
        msg = await ticket_service.add_message(
            db, ticket_id,
            MessageCreate(body=response_text, is_internal=False, sender_type="agent"),
        )
        result = {"ticket_id": ticket_id, "message_id": msg.id, "is_internal": False, "action": action_type}
        if citations:
            result["citations"] = citations
        return result

    # ── Escalate ───────────────────────────────────────────────────────────
    if tool_name == "escalate":
        ticket = await ticket_service.escalate_ticket(db, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        escalation_note = payload.get("escalation_note", "")
        if escalation_note:
            await ticket_service.add_message(
                db, ticket_id,
                MessageCreate(body=escalation_note, is_internal=True, sender_type="agent"),
            )
        return {"ticket_id": ticket_id, "status": "in_progress", "action": "escalate"}

    # ── add_internal_note (direct, no tool mapping) ────────────────────────
    if action_type == "add_internal_note":
        msg = await ticket_service.add_message(
            db, ticket_id,
            MessageCreate(body=response_text, is_internal=True, sender_type="agent"),
        )
        return {"ticket_id": ticket_id, "message_id": msg.id, "is_internal": True, "action": "add_internal_note"}

    # ── no_action / noop ───────────────────────────────────────────────────
    if action_type in ("no_action", "noop"):
        return {"action": "no_action", "skipped": True}

    # ── Fallback: delegate to tool_service ─────────────────────────────────
    from app.services.tool_service import invoke_tool

    arguments = payload.get("arguments") or {}
    res = await invoke_tool(
        db, action.ai_run_id, ticket_id, tool_name,
        arguments=arguments,
        requester_user_id=executor_user_id,
        force_execute=True,
    )
    return {"action": action_type, "result": res}
