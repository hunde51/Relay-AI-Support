"""Phase 12 — Billing & Plan Limits: add limit fields to organization_settings

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organization_settings", sa.Column("monthly_ticket_limit", sa.Integer(), nullable=True))
    op.add_column("organization_settings", sa.Column("api_rate_limit", sa.Integer(), nullable=True))
    op.add_column("organization_settings", sa.Column("max_knowledge_docs", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("organization_settings", "max_knowledge_docs")
    op.drop_column("organization_settings", "api_rate_limit")
    op.drop_column("organization_settings", "monthly_ticket_limit")
