from enum import Enum
from datetime import UTC, datetime
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    waiting_on_customer = "waiting_on_customer"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketCategory(str, Enum):
    billing = "billing"
    technical = "technical"
    general = "general"
    account = "account"


class Ticket(BaseModel):
    id: str
    title: str
    message: str
    status: TicketStatus = TicketStatus.open
    priority: TicketPriority = TicketPriority.medium
    category: TicketCategory = TicketCategory.general
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
