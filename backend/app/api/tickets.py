from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.ticket import (
    MessageCreate, MessageResponse, PaginatedTickets,
    TicketCreate, TicketFilters, TicketResponse, TicketUpdate,
    TicketEventResponse,
)
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.services import ticket_service
from app.api.auth import optional_current_user
from app.core.tenant import assert_org_access

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", status_code=201, response_model=TicketResponse)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    return await ticket_service.create_ticket(db, data, current_user=current_user)


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    category: Optional[TicketCategory] = Query(None),
    assignee_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    sort: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    filters = TicketFilters(
        status=status, priority=priority, category=category,
        assignee_id=assignee_id, customer_id=customer_id,
        search=search, created_from=created_from, created_to=created_to,
        sort=sort, page=page, page_size=page_size,
    )
    items, total, pages = await ticket_service.get_all_tickets(db, filters, current_user=current_user)
    return PaginatedTickets(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    existing = await ticket_service.get_ticket(db, ticket_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(existing.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = await ticket_service.update_ticket(db, ticket_id, data)
    return ticket


@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    ticket_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    msg = await ticket_service.add_message(db, ticket_id, data)
    return msg


@router.get("/{ticket_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await ticket_service.get_messages(db, ticket_id)


@router.get("/{ticket_id}/timeline", response_model=list[TicketEventResponse])
async def get_timeline(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await ticket_service.get_timeline(db, ticket_id)


class AssignRequest(BaseModel):
    assignee_id: str


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: str,
    data: AssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = await ticket_service.assign_ticket(db, ticket_id, data.assignee_id)
    return ticket


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = await ticket_service.resolve_ticket(db, ticket_id)
    return ticket


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = await ticket_service.close_ticket(db, ticket_id)
    return ticket


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(optional_current_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    try:
        assert_org_access(ticket.organization_id, current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = await ticket_service.escalate_ticket(db, ticket_id)
    return ticket
