from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


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


class CustomerORM(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("CUS"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String)
    company: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)

    organization: Mapped["OrganizationORM"] = relationship(back_populates="customers")
    tickets: Mapped[list["TicketORM"]] = relationship(back_populates="customer")

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_customers_organization_email"),
        Index("ix_customers_organization_id", "organization_id"),
    )


class TicketORM(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Kept for Phase 1 compatibility; Phase 2 moves replies into ticket_messages.
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

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


class KnowledgeSourceORM(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("SRC"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    documents: Mapped[list["KnowledgeDocumentORM"]] = relationship(back_populates="source")

    __table_args__ = (Index("ix_knowledge_sources_organization_id", "organization_id"),)


class KnowledgeDocumentORM(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("DOC"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String)
    checksum: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)

    source: Mapped["KnowledgeSourceORM"] = relationship(back_populates="documents")
    chunks: Mapped[list["KnowledgeChunkORM"]] = relationship(back_populates="document")

    __table_args__ = (Index("ix_knowledge_documents_organization_id", "organization_id"),)


class KnowledgeChunkORM(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("CHK"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    token_count: Mapped[str | None] = mapped_column(String)
    embedding_id: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    document: Mapped["KnowledgeDocumentORM"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
        Index("ix_knowledge_chunks_organization_id", "organization_id"),
    )


class KnowledgeIngestionJobORM(TimestampMixin, Base):
    __tablename__ = "knowledge_ingestion_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("ING"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)


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


class AIToolDefinitionORM(TimestampMixin, Base):
    __tablename__ = "ai_tool_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("TDL"))
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String)
    signature: Mapped[dict | None] = mapped_column(JSON)
    tool_type: Mapped[str] = mapped_column(String, default="read", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_ai_tool_definitions_name", "name"),)


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


class ApiKeyORM(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: make_id("AK"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

    organization: Mapped["OrganizationORM"] = relationship()

    __table_args__ = (Index("ix_api_keys_organization_id", "organization_id"),)


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
