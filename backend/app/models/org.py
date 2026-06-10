from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, make_id


class OrganizationORM(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("ORG"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String, default="starter", nullable=False)
    region: Mapped[str] = mapped_column(String, default="local", nullable=False)

    users: Mapped[list["UserORM"]] = relationship(back_populates="organization")
    customers: Mapped[list["CustomerORM"]] = relationship(back_populates="organization")
    tickets: Mapped[list["TicketORM"]] = relationship(back_populates="organization")


class UserORM(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("USR"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="agent", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["OrganizationORM"] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_organization_email"),
        Index("ix_users_organization_id", "organization_id"),
    )


class OrganizationSettingsORM(TimestampMixin, Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_resolve_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_approval_threshold: Mapped[str] = mapped_column(String, default="0.85", nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON)


class NotificationSettingsORM(TimestampMixin, Base):
    __tablename__ = "notification_settings"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    email_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    slack_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_incidents_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON)


class IntegrationORM(TimestampMixin, Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("INT"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="disabled", nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_integrations_organization_provider"),
    )


# forward-reference imports resolved at module level
from app.models.customer import CustomerORM  # noqa: E402
from app.models.ticket import TicketORM  # noqa: E402
