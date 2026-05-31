from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory


class TicketCreate(BaseModel):
    title: str
    message: str
    priority: TicketPriority = TicketPriority.medium
    category: TicketCategory = TicketCategory.general


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None


class TicketFilters(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assignee_id: Optional[str] = None
    customer_id: Optional[str] = None
    search: Optional[str] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    sort: Optional[str] = None  # "created_at_asc" | "created_at_desc" | "updated_at_desc"
    page: int = 1
    page_size: int = 25


class MessageCreate(BaseModel):
    body: str
    is_internal: bool = False
    sender_type: Literal["customer", "agent", "ai", "system"] = "agent"


class TicketResponse(BaseModel):
    id: str
    title: str
    message: str
    status: str
    priority: str
    category: str
    source: str
    sentiment: Optional[str]
    summary: Optional[str]
    organization_id: Optional[str]
    customer_id: Optional[str]
    assignee_id: Optional[str]
    sla_due_at: Optional[datetime]
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    ticket_id: str
    sender_type: str
    sender_user_id: Optional[str]
    sender_customer_id: Optional[str]
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketEventResponse(BaseModel):
    id: str
    ticket_id: str
    actor_type: str
    actor_user_id: Optional[str]
    event_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTickets(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    pages: int
