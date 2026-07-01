"""Phase 11 — usage tracking tables

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("tickets_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ai_runs_executed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("llm_prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("llm_completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("llm_cost_usd", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("api_requests", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "period", name="uq_usage_records_org_period"),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"], unique=False)
    op.create_index("ix_usage_records_period", "usage_records", ["period"], unique=False)

    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_organization_id", "usage_events", ["organization_id"], unique=False)
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"], unique=False)

    op.add_column("ai_runs", sa.Column("model_name", sa.String(), nullable=True))
    op.add_column("ai_runs", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("completion_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_runs", "completion_tokens")
    op.drop_column("ai_runs", "prompt_tokens")
    op.drop_column("ai_runs", "model_name")

    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_organization_id", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_usage_records_period", table_name="usage_records")
    op.drop_index("ix_usage_records_organization_id", table_name="usage_records")
    op.drop_table("usage_records")
