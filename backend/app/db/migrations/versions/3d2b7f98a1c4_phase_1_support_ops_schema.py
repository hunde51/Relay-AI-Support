"""phase 1 support ops schema

Revision ID: 3d2b7f98a1c4
Revises: 9f38a46a19e2
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d2b7f98a1c4"
down_revision: Union[str, None] = "9f38a46a19e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), server_default="starter", nullable=False),
        sa.Column("region", sa.String(), server_default="local", nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), server_default="agent", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_organization_email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"], unique=False)

    op.create_table(
        "customers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_customers_organization_email"),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"], unique=False)

    op.add_column("tickets", sa.Column("organization_id", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("customer_id", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("assignee_id", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("source", sa.String(), server_default="manual", nullable=False))
    op.add_column("tickets", sa.Column("sentiment", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("sla_due_at", sa.DateTime(), nullable=True))
    op.add_column("tickets", sa.Column("first_response_at", sa.DateTime(), nullable=True))
    op.add_column("tickets", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    op.add_column("tickets", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "tickets",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"], unique=False)
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"], unique=False)
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"], unique=False)
    op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)
    op.create_index("ix_tickets_priority", "tickets", ["priority"], unique=False)
    op.create_index("ix_tickets_category", "tickets", ["category"], unique=False)
    op.create_foreign_key("fk_tickets_organization_id", "tickets", "organizations", ["organization_id"], ["id"])
    op.create_foreign_key("fk_tickets_customer_id", "tickets", "customers", ["customer_id"], ["id"])
    op.create_foreign_key("fk_tickets_assignee_id", "tickets", "users", ["assignee_id"], ["id"])

    op.create_table(
        "ticket_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("sender_type", sa.String(), nullable=False),
        sa.Column("sender_user_id", sa.String(), nullable=True),
        sa.Column("sender_customer_id", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["sender_customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ticket_messages_ticket_id_created_at",
        "ticket_messages",
        ["ticket_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ticket_events_ticket_id_created_at",
        "ticket_events",
        ["ticket_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ticket_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("assigned_by_user_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_assignments_ticket_id", "ticket_assignments", ["ticket_id"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_tags_organization_name"),
    )
    op.create_index("ix_tags_organization_id", "tags", ["organization_id"], unique=False)

    op.create_table(
        "ticket_tags",
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("ticket_id", "tag_id"),
    )

    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_sources_organization_id",
        "knowledge_sources",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_documents_organization_id",
        "knowledge_documents",
        ["organization_id"],
        unique=False,
    )
    op.create_index("ix_knowledge_documents_checksum", "knowledge_documents", ["checksum"], unique=False)

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("token_count", sa.String(), nullable=True),
        sa.Column("embedding_id", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_document_index"),
    )
    op.create_index(
        "ix_knowledge_chunks_organization_id",
        "knowledge_chunks",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "knowledge_ingestion_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="queued", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="queued", nullable=False),
        sa.Column("final_decision", sa.String(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_runs_organization_id", "ai_runs", ["organization_id"], unique=False)
    op.create_index("ix_ai_runs_ticket_id_created_at", "ai_runs", ["ticket_id", "created_at"], unique=False)

    op.create_table(
        "ai_steps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ai_run_id", sa.String(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="completed", nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_steps_ai_run_id_created_at", "ai_steps", ["ai_run_id", "created_at"], unique=False)

    op.create_table(
        "ai_tool_calls",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ai_run_id", sa.String(), nullable=False),
        sa.Column("step_id", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), server_default="completed", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"]),
        sa.ForeignKeyConstraint(["step_id"], ["ai_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_tool_calls_ai_run_id", "ai_tool_calls", ["ai_run_id"], unique=False)

    op.create_table(
        "ai_suggested_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ai_run_id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("risk_level", sa.String(), server_default="low", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("approval_status", sa.String(), server_default="pending", nullable=False),
        sa.Column("approved_by_user_id", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_by_user_id", sa.String(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_suggested_actions_ticket_id",
        "ai_suggested_actions",
        ["ticket_id"],
        unique=False,
    )

    op.create_table(
        "ai_responses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ai_run_id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "organization_settings",
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("auto_resolve_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("human_approval_threshold", sa.String(), server_default="0.85", nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    op.create_table(
        "notification_settings",
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("email_digest_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("slack_alerts_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sms_incidents_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    op.create_table(
        "integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="disabled", nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_integrations_organization_provider"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_organization_id_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_organization_id_created_at",
        "notifications",
        ["organization_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_organization_id_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_audit_logs_organization_id_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("integrations")
    op.drop_table("notification_settings")
    op.drop_table("organization_settings")
    op.drop_table("ai_responses")
    op.drop_index("ix_ai_suggested_actions_ticket_id", table_name="ai_suggested_actions")
    op.drop_table("ai_suggested_actions")
    op.drop_index("ix_ai_tool_calls_ai_run_id", table_name="ai_tool_calls")
    op.drop_table("ai_tool_calls")
    op.drop_index("ix_ai_steps_ai_run_id_created_at", table_name="ai_steps")
    op.drop_table("ai_steps")
    op.drop_index("ix_ai_runs_ticket_id_created_at", table_name="ai_runs")
    op.drop_index("ix_ai_runs_organization_id", table_name="ai_runs")
    op.drop_table("ai_runs")
    op.drop_table("knowledge_ingestion_jobs")
    op.drop_index("ix_knowledge_chunks_organization_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_checksum", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_organization_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_knowledge_sources_organization_id", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
    op.drop_table("ticket_tags")
    op.drop_index("ix_tags_organization_id", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_ticket_assignments_ticket_id", table_name="ticket_assignments")
    op.drop_table("ticket_assignments")
    op.drop_index("ix_ticket_events_ticket_id_created_at", table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_index("ix_ticket_messages_ticket_id_created_at", table_name="ticket_messages")
    op.drop_table("ticket_messages")
    op.drop_constraint("fk_tickets_assignee_id", "tickets", type_="foreignkey")
    op.drop_constraint("fk_tickets_customer_id", "tickets", type_="foreignkey")
    op.drop_constraint("fk_tickets_organization_id", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_assignee_id", table_name="tickets")
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_index("ix_tickets_organization_id", table_name="tickets")
    op.drop_column("tickets", "updated_at")
    op.drop_column("tickets", "closed_at")
    op.drop_column("tickets", "resolved_at")
    op.drop_column("tickets", "first_response_at")
    op.drop_column("tickets", "sla_due_at")
    op.drop_column("tickets", "summary")
    op.drop_column("tickets", "sentiment")
    op.drop_column("tickets", "source")
    op.drop_column("tickets", "assignee_id")
    op.drop_column("tickets", "customer_id")
    op.drop_column("tickets", "organization_id")
    op.drop_index("ix_customers_organization_id", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
