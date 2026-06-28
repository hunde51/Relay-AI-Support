from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketMessageORM
from app.schemas.ticket import MessageCreate
from app.repositories.ticket_repository.crud import get_by_id


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def add_message(db: AsyncSession, ticket_id: str, data: MessageCreate) -> TicketMessageORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    msg = TicketMessageORM(
        ticket_id=ticket_id,
        sender_type=data.sender_type,
        body=data.body,
        is_internal=data.is_internal,
    )
    db.add(msg)
    if not ticket.first_response_at and data.sender_type == "agent":
        ticket.first_response_at = _utc_now()
    ticket.updated_at = _utc_now()
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, ticket_id: str) -> list[TicketMessageORM]:
    result = await db.execute(
        select(TicketMessageORM)
        .where(TicketMessageORM.ticket_id == ticket_id)
        .order_by(TicketMessageORM.created_at)
    )
    return result.scalars().all()
