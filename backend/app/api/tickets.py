from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import TicketORM
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", status_code=201)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db)):
    return await ticket_service.create_ticket(db, data)


@router.get("")
async def list_tickets(db: AsyncSession = Depends(get_db)):
    return await ticket_service.get_all_tickets(db)


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}")
async def update_ticket(ticket_id: str, data: TicketUpdate, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.update_ticket(db, ticket_id, data)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
