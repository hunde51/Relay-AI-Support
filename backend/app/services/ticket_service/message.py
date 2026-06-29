from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ticket import MessageCreate
from app.repositories import ticket_repository
from app.services import email_service


async def add_message(db: AsyncSession, ticket_id: str, data: MessageCreate):
    msg = await ticket_repository.add_message(db, ticket_id, data)
    if msg:
        # If the ticket is email-sourced, send the reply back through the provider
        await email_service.send_reply(db, ticket_id, data.body)
    return msg


async def get_messages(db: AsyncSession, ticket_id: str):
    return await ticket_repository.get_messages(db, ticket_id)
