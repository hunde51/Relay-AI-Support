from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import AIRunORM, AIToolCallORM, TicketORM, AISuggestedActionORM, AuditLogORM
from app.services import ai_service
from app.api.auth import get_current_user, optional_current_user
from fastapi import Request
from sqlalchemy import func
from app.core.tenant import assert_org_access

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tools")
async def list_tools():
    # Combine runtime registry and DB definitions if available
    from app.services.tool_service import TOOL_REGISTRY
    tools = [{"name": k, "type": v.get("type", "read"), "description": v.get("description", "")} for k, v in TOOL_REGISTRY.items()]
    return tools


@router.post("/tools/{tool_name}/invoke")
async def invoke_tool_api(tool_name: str, payload: dict, db: AsyncSession = Depends(get_db)):
    # payload: { ai_run_id?, ticket_id?, arguments?, requester_user_id?, confidence? }
    from app.services.tool_service import invoke_tool
    ai_run_id = payload.get("ai_run_id")
    ticket_id = payload.get("ticket_id")
    arguments = payload.get("arguments") or {}
    # ensure ticket_id is available to tool handlers via arguments
    if ticket_id and "ticket_id" not in arguments:
        arguments["ticket_id"] = ticket_id
    requester_user_id = payload.get("requester_user_id")
    confidence = payload.get("confidence")
    result = await invoke_tool(db, ai_run_id, ticket_id, tool_name, arguments=arguments, requester_user_id=requester_user_id, confidence=confidence)
    return result


@router.post("/tickets/{ticket_id}/run")
async def run_ai(ticket_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    # enforce organization scoping when authenticated
    if current_user:
        # verify ticket belongs to same org
        from app.db.models import TicketORM
        result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket.organization_id and ticket.organization_id != current_user.get("organization_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    return await ai_service.run_ai_on_ticket(db, ticket_id)


async def _assert_run_access(db: AsyncSession, run_id: str, current_user: dict | None):
    result = await db.execute(select(AIRunORM).where(AIRunORM.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="AI run not found")
    if current_user:
        ticket = await db.get(TicketORM, run.ticket_id)
        if ticket and ticket.organization_id:
            try:
                assert_org_access(ticket.organization_id, current_user)
            except PermissionError:
                raise HTTPException(status_code=403, detail="Forbidden")
    return run


@router.get("/tickets/{ticket_id}/runs")
async def list_runs(ticket_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    if current_user:
        result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket and ticket.organization_id:
            try:
                assert_org_access(ticket.organization_id, current_user)
            except PermissionError:
                raise HTTPException(status_code=403, detail="Forbidden")
    runs = await ai_service.get_runs_for_ticket(db, ticket_id)
    return [
        {
            "id": r.id,
            "status": r.status,
            "final_decision": r.final_decision,
            "confidence": r.confidence,
            "risk_level": r.risk_level,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "error": r.error,
            "created_at": r.created_at,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    run = await _assert_run_access(db, run_id, current_user)
    return {
        "id": run.id, "ticket_id": run.ticket_id, "status": run.status,
        "final_decision": run.final_decision, "confidence": run.confidence,
        "risk_level": run.risk_level, "started_at": run.started_at,
        "completed_at": run.completed_at, "error": run.error,
        "created_at": run.created_at,
    }


@router.get("/runs/{run_id}/tool-calls")
async def get_tool_calls(run_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    await _assert_run_access(db, run_id, current_user)
    result = await db.execute(
        select(AIToolCallORM)
        .where(AIToolCallORM.ai_run_id == run_id)
        .order_by(AIToolCallORM.created_at)
    )
    calls = result.scalars().all()
    return [
        {
            "id": c.id, "tool_name": c.tool_name, "arguments": c.arguments,
            "result": c.result, "status": c.status, "error": c.error,
            "created_at": c.created_at,
        }
        for c in calls
    ]


@router.get("/runs/{run_id}/steps")
async def get_steps(run_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    await _assert_run_access(db, run_id, current_user)
    steps = await ai_service.get_run_steps(db, run_id)
    return [
        {
            "id": s.id,
            "step_name": s.step_name,
            "status": s.status,
            "output": s.output,
            "confidence": s.confidence,
            "created_at": s.created_at,
        }
        for s in steps
    ]


@router.get("/tickets/{ticket_id}/suggested-actions")
async def get_suggested_actions(ticket_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    if current_user:
        result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket and ticket.organization_id:
            try:
                assert_org_access(ticket.organization_id, current_user)
            except PermissionError:
                raise HTTPException(status_code=403, detail="Forbidden")
    actions = await ai_service.get_suggested_actions(db, ticket_id)
    return [
        {
            "id": a.id,
            "action_type": a.action_type,
            "payload": a.payload,
            "risk_level": a.risk_level,
            "requires_approval": a.requires_approval,
            "approval_status": a.approval_status,
            "approved_at": a.approved_at,
            "rejected_at": a.rejected_at,
            "created_at": a.created_at,
        }
        for a in actions
    ]


@router.get("/runs/{run_id}/suggested-actions")
async def get_run_suggested_actions(run_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    await _assert_run_access(db, run_id, current_user)
    actions = await ai_service.get_suggested_actions_for_run(db, run_id)
    return [
        {
            "id": a.id,
            "ai_run_id": a.ai_run_id,
            "ticket_id": a.ticket_id,
            "action_type": a.action_type,
            "payload": a.payload,
            "risk_level": a.risk_level,
            "requires_approval": a.requires_approval,
            "approval_status": a.approval_status,
            "approved_by_user_id": a.approved_by_user_id,
            "approved_at": a.approved_at,
            "rejected_by_user_id": a.rejected_by_user_id,
            "rejected_at": a.rejected_at,
            "created_at": a.created_at,
        }
        for a in actions
    ]


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, payload: dict | None = None, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    # payload may contain { "actor_user_id": "USR-..." }
    actor_user_id = payload.get("actor_user_id") if payload else (current_user.get("user_id") if current_user else None)
    # if current_user present, ensure action belongs to their org
    if current_user:
        from app.db.models import AISuggestedActionORM
        res = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
        act = res.scalar_one_or_none()
        if not act:
            raise HTTPException(status_code=404, detail="Action not found")
        # load ticket to check org
        from app.db.models import TicketORM
        t = await db.get(TicketORM, act.ticket_id)
        if t and t.organization_id and t.organization_id != current_user.get("organization_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    action = await ai_service.approve_action(db, action_id, actor_user_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or unauthorized")
    return {"id": action.id, "approval_status": action.approval_status}


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: str, payload: dict | None = None, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    actor_user_id = payload.get("actor_user_id") if payload else (current_user.get("user_id") if current_user else None)
    if current_user:
        from app.db.models import AISuggestedActionORM, TicketORM
        res = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
        act = res.scalar_one_or_none()
        if not act:
            raise HTTPException(status_code=404, detail="Action not found")
        t = await db.get(TicketORM, act.ticket_id)
        if t and t.organization_id and t.organization_id != current_user.get("organization_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    action = await ai_service.reject_action(db, action_id, actor_user_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or unauthorized")
    return {"id": action.id, "approval_status": action.approval_status}


@router.post("/actions/{action_id}/execute")
async def execute_action(action_id: str, payload: dict | None = None, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    executor_user_id = payload.get("executor_user_id") if payload else (current_user.get("user_id") if current_user else None)
    if current_user:
        from app.db.models import AISuggestedActionORM, TicketORM
        res = await db.execute(select(AISuggestedActionORM).where(AISuggestedActionORM.id == action_id))
        act = res.scalar_one_or_none()
        if not act:
            raise HTTPException(status_code=404, detail="Action not found")
        t = await db.get(TicketORM, act.ticket_id)
        if t and t.organization_id and t.organization_id != current_user.get("organization_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    result = await ai_service.execute_suggested_action(db, action_id, executor_user_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/tickets/{ticket_id}/audits")
async def get_audit_logs(ticket_id: str, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    if current_user:
        result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket and ticket.organization_id:
            try:
                assert_org_access(ticket.organization_id, current_user)
            except PermissionError:
                raise HTTPException(status_code=403, detail="Forbidden")
    # Return audit logs where metadata.ticket_id matches
    q = select(AuditLogORM).where(AuditLogORM.metadata_json["ticket_id"].astext == ticket_id).order_by(AuditLogORM.created_at.desc())
    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "actor_type": l.actor_type,
            "actor_user_id": l.actor_user_id,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "metadata": l.metadata_json,
            "created_at": l.created_at,
        }
        for l in logs
    ]



@router.get("/metrics")
async def get_metrics(org_id: str | None = None, db: AsyncSession = Depends(get_db), current_user: dict | None = Depends(optional_current_user)):
    # Simple metrics: count audit actions grouped by action (optionally filtered by org)
    if current_user and org_id:
        try:
            assert_org_access(org_id, current_user)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Forbidden")
    q = select(AuditLogORM.action, func.count(AuditLogORM.id)).group_by(AuditLogORM.action)
    if org_id:
        q = q.where(AuditLogORM.organization_id == org_id)
    result = await db.execute(q)
    rows = result.all()
    return {r[0]: r[1] for r in rows}
