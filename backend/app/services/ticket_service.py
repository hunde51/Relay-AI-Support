from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import MessageCreate, TicketCreate, TicketFilters, TicketUpdate
from app.repositories import ticket_repository
from app.core.ws_manager import manager


async def create_ticket(db: AsyncSession, data: TicketCreate, current_user: dict | None = None):
    ticket = await ticket_repository.create(db, data, current_user=current_user)
    await manager.broadcast_ticket({"event": "ticket_created", "ticket_id": ticket.id, "status": ticket.status})
    return ticket


async def get_all_tickets(db: AsyncSession, filters: TicketFilters, current_user: dict | None = None):
    return await ticket_repository.get_all(db, filters, current_user=current_user)


async def get_ticket(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_by_id(db, ticket_id)


async def update_ticket(db: AsyncSession, ticket_id: str, data: TicketUpdate):
    ticket = await ticket_repository.update(db, ticket_id, data)
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_updated", "ticket_id": ticket.id, "status": ticket.status})
    return ticket


async def resolve_ticket(db: AsyncSession, ticket_id: str):
    ticket = await ticket_repository.set_status(db, ticket_id, "resolved", "ticket_resolved")
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_resolved", "ticket_id": ticket.id})
    return ticket


async def close_ticket(db: AsyncSession, ticket_id: str):
    return await ticket_repository.set_status(db, ticket_id, "closed", "ticket_closed")


async def escalate_ticket(db: AsyncSession, ticket_id: str):
    ticket = await ticket_repository.set_status(db, ticket_id, "in_progress", "ticket_escalated")
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_escalated", "ticket_id": ticket.id})
    return ticket


async def assign_ticket(db: AsyncSession, ticket_id: str, assignee_id: str):
    ticket = await ticket_repository.assign(db, ticket_id, assignee_id)
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_assigned", "ticket_id": ticket.id, "assignee_id": assignee_id})
    return ticket


async def add_message(db: AsyncSession, ticket_id: str, data: MessageCreate):
    return await ticket_repository.add_message(db, ticket_id, data)


async def get_messages(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_messages(db, ticket_id)


async def get_timeline(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_timeline(db, ticket_id)
