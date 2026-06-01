from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import AIRunORM, AIToolCallORM
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tools")
async def list_tools():
    # Combine runtime registry and DB definitions if available
    from app.services.tool_service import TOOL_REGISTRY
    tools = [{"name": k, "type": v.get("type", "read"), "description": ""} for k, v in TOOL_REGISTRY.items()]
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
async def run_ai(ticket_id: str, db: AsyncSession = Depends(get_db)):
    return await ai_service.run_ai_on_ticket(db, ticket_id)


@router.get("/tickets/{ticket_id}/runs")
async def list_runs(ticket_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIRunORM).where(AIRunORM.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="AI run not found")
    return {
        "id": run.id, "ticket_id": run.ticket_id, "status": run.status,
        "final_decision": run.final_decision, "confidence": run.confidence,
        "risk_level": run.risk_level, "started_at": run.started_at,
        "completed_at": run.completed_at, "error": run.error,
        "created_at": run.created_at,
    }


@router.get("/runs/{run_id}/tool-calls")
async def get_tool_calls(run_id: str, db: AsyncSession = Depends(get_db)):
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



async def get_steps(run_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_suggested_actions(ticket_id: str, db: AsyncSession = Depends(get_db)):
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


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, db: AsyncSession = Depends(get_db)):
    action = await ai_service.approve_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return {"id": action.id, "approval_status": action.approval_status}


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: str, db: AsyncSession = Depends(get_db)):
    action = await ai_service.reject_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return {"id": action.id, "approval_status": action.approval_status}


@router.post("/actions/{action_id}/execute")
async def execute_action(action_id: str, db: AsyncSession = Depends(get_db)):
    result = await ai_service.execute_suggested_action(db, action_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
