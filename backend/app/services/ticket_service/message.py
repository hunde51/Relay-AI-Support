from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import MessageCreate
from app.repositories import ticket_repository


async def add_message(db: AsyncSession, ticket_id: str, data: MessageCreate):
    return await ticket_repository.add_message(db, ticket_id, data)


async def get_messages(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_messages(db, ticket_id)
