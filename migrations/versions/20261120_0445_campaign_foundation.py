"""create campaign foundation and domain audit events

Revision ID: 5f3a9d8c1b42
Revises: 4a7c2e1d9f60
Create Date: 2026-11-20 04:45:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "5f3a9d8c1b42"
down_revision: Union[str, Sequence[str], None] = "4a7c2e1d9f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=11),
            server_default="PREPARATION",
            nullable=False,
        ),
        sa.Column("duration_category", sa.String(length=9), nullable=False),
        sa.Column(
            "planned_session_duration_minutes",
            sa.Integer(),
            server_default="180",
            nullable=False,
        ),
        sa.Column("frequency", sa.String(length=9), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("estimated_completion_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(name) >= 1 AND length(name) <= 100",
            name="ck_campaigns_name_length",
        ),
        sa.CheckConstraint(
            "status IN ('PREPARATION', 'ACTIVE', 'PAUSED', 'ENDED')",
            name="ck_campaigns_status",
        ),
        sa.CheckConstraint(
            "duration_category IN ('ONE_SHOT', 'SHORT', 'MEDIUM', 'LONG')",
            name="ck_campaigns_duration_category",
        ),
        sa.CheckConstraint(
            "frequency IN ('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'IRREGULAR')",
            name="ck_campaigns_frequency",
        ),
        sa.CheckConstraint(
            "planned_session_duration_minutes >= 120 "
            "AND planned_session_duration_minutes <= 240",
            name="ck_campaigns_session_duration",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR estimated_completion_date IS NULL "
            "OR estimated_completion_date >= start_date",
            name="ck_campaigns_completion_date",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_owner_user_id", "campaigns", ["owner_user_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

    op.create_table(
        "campaign_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campaign_audit_events_campaign_id",
        "campaign_audit_events",
        ["campaign_id"],
    )
    op.create_index(
        "ix_campaign_audit_events_actor_user_id",
        "campaign_audit_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_campaign_audit_events_created_at",
        "campaign_audit_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_audit_events_created_at", table_name="campaign_audit_events")
    op.drop_index("ix_campaign_audit_events_actor_user_id", table_name="campaign_audit_events")
    op.drop_index("ix_campaign_audit_events_campaign_id", table_name="campaign_audit_events")
    op.drop_table("campaign_audit_events")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_owner_user_id", table_name="campaigns")
    op.drop_table("campaigns")
