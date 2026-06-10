from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id


class WebhookEndpointORM(TimestampMixin, Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("WHK"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    secret: Mapped[str] = mapped_column(String, nullable=False)   # HMAC signing secret
    events: Mapped[list] = mapped_column(JSON, nullable=False)    # ["ticket.created", ...]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    deliveries: Mapped[list["WebhookDeliveryORM"]] = relationship(back_populates="endpoint")

    __table_args__ = (Index("ix_webhook_endpoints_organization_id", "organization_id"),)


class WebhookDeliveryORM(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("WHD"))
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending|delivered|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    endpoint: Mapped["WebhookEndpointORM"] = relationship(back_populates="deliveries")

    __table_args__ = (Index("ix_webhook_deliveries_endpoint_id", "endpoint_id"),)
