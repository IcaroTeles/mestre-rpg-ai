"""add one-time user invites

Revision ID: 4a7c2e1d9f60
Revises: 9c41d7e2a8f5
Create Date: 2026-11-20 03:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4a7c2e1d9f60"
down_revision: Union[str, Sequence[str], None] = "9c41d7e2a8f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("used_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="player"),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("purpose = 'player'", name="ck_user_invites_player_purpose"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["used_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_user_invites_token_hash", "user_invites", ["token_hash"], unique=True)
    op.create_index("ix_user_invites_created_by_user_id", "user_invites", ["created_by_user_id"])
    op.create_index("ix_user_invites_used_by_user_id", "user_invites", ["used_by_user_id"])
    op.create_index("ix_user_invites_expires_at", "user_invites", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_user_invites_expires_at", table_name="user_invites")
    op.drop_index("ix_user_invites_used_by_user_id", table_name="user_invites")
    op.drop_index("ix_user_invites_created_by_user_id", table_name="user_invites")
    op.drop_index("uq_user_invites_token_hash", table_name="user_invites")
    op.drop_table("user_invites")
