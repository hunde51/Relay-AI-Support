from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id, utc_now


# ── Enums (used by Pydantic schemas and ORM) ──────────────────────────────────

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


# ── Pydantic model (kept for legacy use) ─────────────────────────────────────

class Ticket(BaseModel):
    id: str
    title: str
    message: str
    status: TicketStatus = TicketStatus.open
    priority: TicketPriority = TicketPriority.medium
    category: TicketCategory = TicketCategory.general
    created_at: datetime = Field(default_factory=lambda: datetime.now())


# ── ORM models ────────────────────────────────────────────────────────────────

class TicketORM(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, default="general", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(Text)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    organization: Mapped["OrganizationORM | None"] = relationship(back_populates="tickets")
    customer: Mapped["CustomerORM | None"] = relationship(back_populates="tickets")
    assignee: Mapped["UserORM | None"] = relationship()
    messages: Mapped[list["TicketMessageORM"]] = relationship(back_populates="ticket")
    events: Mapped[list["TicketEventORM"]] = relationship(back_populates="ticket")
    ai_runs: Mapped[list["AIRunORM"]] = relationship(back_populates="ticket")


class TicketMessageORM(TimestampMixin, Base):
    __tablename__ = "ticket_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("MSG"))
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String, nullable=False)
    sender_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    sender_customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped["TicketORM"] = relationship(back_populates="messages")
    sender_user: Mapped["UserORM | None"] = relationship(foreign_keys=[sender_user_id])
    sender_customer: Mapped["CustomerORM | None"] = relationship(foreign_keys=[sender_customer_id])

    __table_args__ = (Index("ix_ticket_messages_ticket_id_created_at", "ticket_id", "created_at"),)


class TicketEventORM(Base):
    __tablename__ = "ticket_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("EVT"))
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    ticket: Mapped["TicketORM"] = relationship(back_populates="events")
    actor_user: Mapped["UserORM | None"] = relationship()

    __table_args__ = (Index("ix_ticket_events_ticket_id_created_at", "ticket_id", "created_at"),)


class TicketAssignmentORM(Base):
    __tablename__ = "ticket_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("ASN"))
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("ix_ticket_assignments_ticket_id", "ticket_id"),)


class TagORM(TimestampMixin, Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("TAG"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_tags_organization_name"),
        Index("ix_tags_organization_id", "organization_id"),
    )


class TicketTagORM(Base):
    __tablename__ = "ticket_tags"

    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


# resolve forward references
from app.models.org import OrganizationORM, UserORM  # noqa: E402
from app.models.customer import CustomerORM  # noqa: E402
from app.models.ai import AIRunORM  # noqa: E402
