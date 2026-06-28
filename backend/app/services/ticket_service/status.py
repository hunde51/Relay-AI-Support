from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import ticket_repository
from app.core.ws_manager import manager
from app.services.ticket_service.webhook import _fire_webhook


async def resolve_ticket(db: AsyncSession, ticket_id: str):
    ticket = await ticket_repository.set_status(db, ticket_id, "resolved", "ticket_resolved")
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_resolved", "ticket_id": ticket.id})
        await _fire_webhook(db, ticket, "ticket.resolved")
    return ticket


async def close_ticket(db: AsyncSession, ticket_id: str):
    ticket = await ticket_repository.set_status(db, ticket_id, "closed", "ticket_closed")
    if ticket:
        await _fire_webhook(db, ticket, "ticket.updated", {"status": "closed"})
    return ticket


async def escalate_ticket(db: AsyncSession, ticket_id: str):
    ticket = await ticket_repository.set_status(db, ticket_id, "in_progress", "ticket_escalated")
    if ticket:
        await manager.broadcast_ticket({"event": "ticket_escalated", "ticket_id": ticket.id})
        await _fire_webhook(db, ticket, "ticket.updated", {"status": "in_progress"})
    return ticket
