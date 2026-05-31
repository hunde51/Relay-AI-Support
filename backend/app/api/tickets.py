from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.ticket import (
    MessageCreate, MessageResponse, PaginatedTickets,
    TicketCreate, TicketFilters, TicketResponse, TicketUpdate,
    TicketEventResponse,
)
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", status_code=201, response_model=TicketResponse)
async def create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db)):
    return await ticket_service.create_ticket(db, data)


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    category: Optional[TicketCategory] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = TicketFilters(status=status, priority=priority, category=category, search=search, page=page, page_size=page_size)
    items, total, pages = await ticket_service.get_all_tickets(db, filters)
    return PaginatedTickets(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, data: TicketUpdate, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.update_ticket(db, ticket_id, data)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(ticket_id: str, data: MessageCreate, db: AsyncSession = Depends(get_db)):
    msg = await ticket_service.add_message(db, ticket_id, data)
    if not msg:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return msg


@router.get("/{ticket_id}/messages", response_model=list[MessageResponse])
async def get_messages(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await ticket_service.get_messages(db, ticket_id)


@router.get("/{ticket_id}/timeline", response_model=list[TicketEventResponse])
async def get_timeline(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await ticket_service.get_timeline(db, ticket_id)


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.resolve_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.close_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.escalate_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
