from pydantic import BaseModel
from typing import Optional
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
