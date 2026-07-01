from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, make_id, utc_now


class UsageRecordORM(Base):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("USG"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    tickets_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_runs_executed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    api_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "period", name="uq_usage_records_org_period"),
        Index("ix_usage_records_organization_id", "organization_id"),
        Index("ix_usage_records_period", "period"),
    )


class UsageEventORM(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("UGE"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_usage_events_organization_id", "organization_id"),
        Index("ix_usage_events_created_at", "created_at"),
    )
