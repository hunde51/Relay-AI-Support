from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketEventORM


async def get_timeline(db: AsyncSession, ticket_id: str) -> list[TicketEventORM]:
    result = await db.execute(
        select(TicketEventORM)
        .where(TicketEventORM.ticket_id == ticket_id)
        .order_by(TicketEventORM.created_at)
    )
    return result.scalars().all()
