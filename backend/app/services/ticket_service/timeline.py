from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import ticket_repository


async def get_timeline(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_timeline(db, ticket_id)
