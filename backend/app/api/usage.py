from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.usage_service import (
    get_ai_costs_breakdown,
    get_usage_history,
    get_usage_limits,
    get_usage_summary,
)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary")
async def usage_summary(
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.get("organization_id")
    if not org_id:
        return {"error": "organization_id required"}
    return await get_usage_summary(db, org_id, period=period)


@router.get("/history")
async def usage_history(
    months: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.get("organization_id")
    if not org_id:
        return {"error": "organization_id required"}
    return await get_usage_history(db, org_id, months=months)


@router.get("/ai-costs")
async def usage_ai_costs(
    months: int = 6,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.get("organization_id")
    if not org_id:
        return {"error": "organization_id required"}
    return await get_ai_costs_breakdown(db, org_id, months=months)


@router.get("/limits")
async def usage_limits(
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.get("organization_id")
    if not org_id:
        return {"error": "organization_id required"}
    return await get_usage_limits(db, org_id, period=period)
