from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services import agent_service
from app.repositories import ticket_repository

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/process/{ticket_id}")
async def process_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_repository.get_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = await agent_service.process_ticket(
        ticket_id=ticket.id,
        title=ticket.title,
        message=ticket.message,
        category=ticket.category,
        priority=ticket.priority,
    )
    return result


@router.get("/logs/{ticket_id}")
async def get_logs(ticket_id: str):
    logs = agent_service.get_logs(ticket_id)
    if not logs:
        raise HTTPException(status_code=404, detail="No agent logs found for this ticket")
    return logs
