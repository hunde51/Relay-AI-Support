from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketEventORM, TicketORM
from app.repositories.ticket_repository.crud import get_by_id


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def set_status(db: AsyncSession, ticket_id: str, status: str, event_type: str) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    old_status = ticket.status
    ticket.status = status
    ticket.updated_at = _utc_now()
    if status == "resolved":
        ticket.resolved_at = _utc_now()
    elif status == "closed":
        ticket.closed_at = _utc_now()
    db.add(TicketEventORM(
        ticket_id=ticket.id,
        actor_type="agent",
        event_type=event_type,
        old_value=old_status,
        new_value=status,
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket
