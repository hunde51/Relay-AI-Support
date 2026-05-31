from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


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


@router.get("/runs/{run_id}/steps")
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
