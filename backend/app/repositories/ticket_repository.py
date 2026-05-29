from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime
from app.db.models import TicketORM
from app.schemas.ticket import TicketCreate, TicketUpdate


async def create(db: AsyncSession, data: TicketCreate) -> TicketORM:
    ticket = TicketORM(
        id=f"TKT-{uuid4().hex[:6].upper()}",
        title=data.title,
        message=data.message,
        priority=data.priority,
        category=data.category,
        created_at=datetime.utcnow(),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_all(db: AsyncSession) -> list[TicketORM]:
    result = await db.execute(select(TicketORM))
    return result.scalars().all()


async def get_by_id(db: AsyncSession, ticket_id: str) -> TicketORM | None:
    result = await db.execute(select(TicketORM).where(TicketORM.id == ticket_id))
    return result.scalar_one_or_none()


async def update(db: AsyncSession, ticket_id: str, data: TicketUpdate) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    await db.commit()
    await db.refresh(ticket)
    return ticket
