from fastapi import APIRouter, Depends
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import UTC, datetime, timedelta

from app.db.database import get_db
from app.db.models import TicketORM, AIRunORM

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/categories")
async def category_distribution(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TicketORM.category, func.count().label("count"))
        .group_by(TicketORM.category)
    )
    return [{"category": row.category, "count": row.count} for row in result.all()]


@router.get("/resolution-trend")
async def resolution_trend(db: AsyncSession = Depends(get_db)):
    """Daily resolved ticket count for the last 14 days."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
    result = await db.execute(
        select(
            func.date(TicketORM.resolved_at).label("day"),
            func.count().label("count"),
        )
        .where(TicketORM.resolved_at >= cutoff)
        .group_by(func.date(TicketORM.resolved_at))
        .order_by(func.date(TicketORM.resolved_at))
    )
    return [{"day": str(row.day), "count": row.count} for row in result.all()]


@router.get("/auto-resolution-rate")
async def auto_resolution_rate(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(AIRunORM))).scalar_one()
    resolved = (
        await db.execute(
            select(func.count()).select_from(AIRunORM).where(AIRunORM.final_decision == "resolve")
        )
    ).scalar_one()
    rate = round(resolved / total, 4) if total else 0.0
    return {"total_ai_runs": total, "auto_resolved": resolved, "rate": rate}


@router.get("/peak-hours")
async def peak_hours(db: AsyncSession = Depends(get_db)):
    """Ticket count grouped by hour-of-day (0–23)."""
    result = await db.execute(
        select(
            func.strftime("%H", TicketORM.created_at).label("hour"),
            func.count().label("count"),
        )
        .group_by(func.strftime("%H", TicketORM.created_at))
        .order_by(func.strftime("%H", TicketORM.created_at))
    )
    return [{"hour": int(row.hour), "count": row.count} for row in result.all()]


@router.get("/sla-performance")
async def sla_performance(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(TicketORM).where(TicketORM.sla_due_at.isnot(None)))).scalar_one()
    breached = (
        await db.execute(
            select(func.count()).select_from(TicketORM).where(
                TicketORM.sla_due_at.isnot(None),
                TicketORM.resolved_at > TicketORM.sla_due_at,
            )
        )
    ).scalar_one()
    met = total - breached
    return {"total_with_sla": total, "met": met, "breached": breached}


@router.get("/agent-performance")
async def agent_performance(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIRunORM.final_decision, func.count().label("count"))
        .where(AIRunORM.status == "completed")
        .group_by(AIRunORM.final_decision)
    )
    return [{"decision": row.final_decision, "count": row.count} for row in result.all()]
