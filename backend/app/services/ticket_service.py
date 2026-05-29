from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.repositories import ticket_repository
from app.core.ws_manager import manager


async def create_ticket(db: AsyncSession, data: TicketCreate):
    ticket = await ticket_repository.create(db, data)
    await manager.broadcast_ticket({"event": "ticket_created", "ticket_id": ticket.id, "title": ticket.title, "status": ticket.status})
    return ticket


async def get_all_tickets(db: AsyncSession):
    return await ticket_repository.get_all(db)


async def get_ticket(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_by_id(db, ticket_id)


async def update_ticket(db: AsyncSession, ticket_id: str, data: TicketUpdate):
    ticket = await ticket_repository.update(db, ticket_id, data)
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_updated", "ticket_id": ticket.id, "status": ticket.status})
    return ticket
