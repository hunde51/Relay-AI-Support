from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id, utc_now


class EmailIntegrationORM(TimestampMixin, Base):
    __tablename__ = "email_integrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("EMI"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # "gmail" | "outlook"
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)

    messages: Mapped[list["EmailMessageORM"]] = relationship(back_populates="integration")

    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_email_integrations_org_provider"),
        Index("ix_email_integrations_organization_id", "organization_id"),
    )


class EmailMessageORM(TimestampMixin, Base):
    __tablename__ = "email_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("EMM"))
    email_integration_id: Mapped[str] = mapped_column(ForeignKey("email_integrations.id"), nullable=False)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"))
    provider_message_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_thread_id: Mapped[str] = mapped_column(String, nullable=False)
    from_address: Mapped[str] = mapped_column(String, nullable=False)
    to_address: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String, default="inbound", nullable=False)  # "inbound" | "outbound"

    integration: Mapped["EmailIntegrationORM"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_email_messages_integration_id", "email_integration_id"),
        Index("ix_email_messages_ticket_id", "ticket_id"),
        Index("ix_email_messages_provider_message_id", "provider_message_id"),
    )


from app.models.ticket import TicketORM  # noqa: E402
