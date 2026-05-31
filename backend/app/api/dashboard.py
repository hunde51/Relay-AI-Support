from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import UTC, datetime, timedelta

from app.db.database import get_db
from app.db.models import TicketORM, TicketEventORM

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    total = (await db.execute(select(func.count()).select_from(TicketORM))).scalar_one()
    open_count = (await db.execute(select(func.count()).select_from(TicketORM).where(TicketORM.status == "open"))).scalar_one()
    in_progress = (await db.execute(select(func.count()).select_from(TicketORM).where(TicketORM.status == "in_progress"))).scalar_one()
    resolved_today = (await db.execute(
        select(func.count()).select_from(TicketORM)
        .where(TicketORM.status == "resolved", TicketORM.resolved_at >= today_start)
    )).scalar_one()

    # avg first response in minutes (tickets that have first_response_at set)
    rows = (await db.execute(
        select(TicketORM.created_at, TicketORM.first_response_at)
        .where(TicketORM.first_response_at.isnot(None))
    )).all()
    avg_response = None
    if rows:
        diffs = [(r.first_response_at - r.created_at).total_seconds() / 60 for r in rows]
        avg_response = round(sum(diffs) / len(diffs), 1)

    return {
        "total_tickets": total,
        "open_tickets": open_count,
        "in_progress_tickets": in_progress,
        "resolved_today": resolved_today,
        "avg_first_response_minutes": avg_response,
    }


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TicketEventORM, TicketORM.title)
        .join(TicketORM, TicketEventORM.ticket_id == TicketORM.id)
        .order_by(TicketEventORM.created_at.desc())
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "event_id": row.TicketEventORM.id,
            "ticket_id": row.TicketEventORM.ticket_id,
            "ticket_title": row.title,
            "event_type": row.TicketEventORM.event_type,
            "actor_type": row.TicketEventORM.actor_type,
            "old_value": row.TicketEventORM.old_value,
            "new_value": row.TicketEventORM.new_value,
            "created_at": row.TicketEventORM.created_at.isoformat(),
        }
        for row in rows
    ]
