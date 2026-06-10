from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, make_id, utc_now


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("AUD"))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("ix_audit_logs_organization_id_created_at", "organization_id", "created_at"),)


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("NTF"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("ix_notifications_organization_id_created_at", "organization_id", "created_at"),)
