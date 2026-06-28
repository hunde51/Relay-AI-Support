from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketEventORM, TicketORM
from app.repositories.ticket_repository.crud import get_by_id


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def assign(db: AsyncSession, ticket_id: str, assignee_id: str) -> TicketORM | None:
    ticket = await get_by_id(db, ticket_id)
    if not ticket:
        return None
    old = ticket.assignee_id
    ticket.assignee_id = assignee_id
    ticket.updated_at = _utc_now()
    db.add(TicketEventORM(
        ticket_id=ticket.id,
        actor_type="agent",
        event_type="assigned",
        old_value=old,
        new_value=assignee_id,
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket
