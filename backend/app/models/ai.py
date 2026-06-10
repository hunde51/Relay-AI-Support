from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, make_id, utc_now


class AIRunORM(Base):
    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("AIR"))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    final_decision: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[str | None] = mapped_column(String)
    risk_level: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    ticket: Mapped["TicketORM"] = relationship(back_populates="ai_runs")
    steps: Mapped[list["AIStepORM"]] = relationship(back_populates="ai_run")
    tool_calls: Mapped[list["AIToolCallORM"]] = relationship(back_populates="ai_run")
    suggested_actions: Mapped[list["AISuggestedActionORM"]] = relationship(back_populates="ai_run")

    __table_args__ = (
        Index("ix_ai_runs_ticket_id_created_at", "ticket_id", "created_at"),
        Index("ix_ai_runs_organization_id", "organization_id"),
    )


class AIStepORM(Base):
    __tablename__ = "ai_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("AIS"))
    ai_run_id: Mapped[str] = mapped_column(ForeignKey("ai_runs.id"), nullable=False)
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text)
    output: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    ai_run: Mapped["AIRunORM"] = relationship(back_populates="steps")

    __table_args__ = (Index("ix_ai_steps_ai_run_id_created_at", "ai_run_id", "created_at"),)


class AIToolCallORM(Base):
    __tablename__ = "ai_tool_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("AIT"))
    ai_run_id: Mapped[str] = mapped_column(ForeignKey("ai_runs.id"), nullable=False)
    step_id: Mapped[str | None] = mapped_column(ForeignKey("ai_steps.id"))
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    arguments: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    ai_run: Mapped["AIRunORM"] = relationship(back_populates="tool_calls")
    step: Mapped["AIStepORM | None"] = relationship()

    __table_args__ = (Index("ix_ai_tool_calls_ai_run_id", "ai_run_id"),)


class AISuggestedActionORM(Base):
    __tablename__ = "ai_suggested_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("ACT"))
    ai_run_id: Mapped[str] = mapped_column(ForeignKey("ai_runs.id"), nullable=False)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    risk_level: Mapped[str] = mapped_column(String, default="low", nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    rejected_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    ai_run: Mapped["AIRunORM"] = relationship(back_populates="suggested_actions")

    __table_args__ = (Index("ix_ai_suggested_actions_ticket_id", "ticket_id"),)


class AIResponseORM(Base):
    __tablename__ = "ai_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("RSP"))
    ai_run_id: Mapped[str] = mapped_column(ForeignKey("ai_runs.id"), nullable=False)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class AIToolDefinitionORM(Base):
    __tablename__ = "ai_tool_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("TDL"))
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String)
    signature: Mapped[dict | None] = mapped_column(JSON)
    tool_type: Mapped[str] = mapped_column(String, default="read", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_ai_tool_definitions_name", "name"),)


# resolve forward references
from app.models.ticket import TicketORM  # noqa: E402
