"""Phase 8 — email integration tables

Revision ID: c5d6e7f8a9b0
Revises: b2c3d4e5f6a7
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("email_address", sa.String(), nullable=False),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_email_integrations_org_provider"),
    )
    op.create_index("ix_email_integrations_organization_id", "email_integrations", ["organization_id"], unique=False)

    op.create_table(
        "email_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email_integration_id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=True),
        sa.Column("provider_message_id", sa.String(), nullable=False),
        sa.Column("provider_thread_id", sa.String(), nullable=False),
        sa.Column("from_address", sa.String(), nullable=False),
        sa.Column("to_address", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("direction", sa.String(), server_default="inbound", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["email_integration_id"], ["email_integrations.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_messages_integration_id", "email_messages", ["email_integration_id"], unique=False)
    op.create_index("ix_email_messages_ticket_id", "email_messages", ["ticket_id"], unique=False)
    op.create_index("ix_email_messages_provider_message_id", "email_messages", ["provider_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_email_messages_provider_message_id", table_name="email_messages")
    op.drop_index("ix_email_messages_ticket_id", table_name="email_messages")
    op.drop_index("ix_email_messages_integration_id", table_name="email_messages")
    op.drop_table("email_messages")
    op.drop_index("ix_email_integrations_organization_id", table_name="email_integrations")
    op.drop_table("email_integrations")
