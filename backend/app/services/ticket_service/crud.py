from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import TicketCreate, TicketFilters, TicketUpdate
from app.repositories import ticket_repository
from app.core.ws_manager import manager
from app.services.ticket_service.webhook import _fire_webhook


async def create_ticket(db: AsyncSession, data: TicketCreate, current_user: dict | None = None):
    ticket = await ticket_repository.create(db, data, current_user=current_user)
    await manager.broadcast_ticket({"event": "ticket_created", "ticket_id": ticket.id, "status": ticket.status})
    await _fire_webhook(db, ticket, "ticket.created")
    return ticket


async def get_all_tickets(db: AsyncSession, filters: TicketFilters, current_user: dict | None = None):
    return await ticket_repository.get_all(db, filters, current_user=current_user)


async def get_ticket(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_by_id(db, ticket_id)


async def update_ticket(db: AsyncSession, ticket_id: str, data: TicketUpdate):
    ticket = await ticket_repository.update(db, ticket_id, data)
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_updated", "ticket_id": ticket.id, "status": ticket.status})
        await _fire_webhook(db, ticket, "ticket.updated")
    return ticket
