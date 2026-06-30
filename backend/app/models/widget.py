from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id


class WidgetKeyORM(TimestampMixin, Base):
    __tablename__ = "widget_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("WKEY"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    allowed_origins: Mapped[list | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)

    organization: Mapped["OrganizationORM"] = relationship()

    __table_args__ = (Index("ix_widget_keys_organization_id", "organization_id"),)
