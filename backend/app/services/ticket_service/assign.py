from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import ticket_repository
from app.core.ws_manager import manager


async def assign_ticket(db: AsyncSession, ticket_id: str, assignee_id: str):
    ticket = await ticket_repository.assign(db, ticket_id, assignee_id)
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_assigned", "ticket_id": ticket.id, "assignee_id": assignee_id})
    return ticket
