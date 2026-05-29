from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.repositories import ticket_repository


async def create_ticket(db: AsyncSession, data: TicketCreate):
    return await ticket_repository.create(db, data)


async def get_all_tickets(db: AsyncSession):
    return await ticket_repository.get_all(db)


async def get_ticket(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_by_id(db, ticket_id)


async def update_ticket(db: AsyncSession, ticket_id: str, data: TicketUpdate):
    return await ticket_repository.update(db, ticket_id, data)
