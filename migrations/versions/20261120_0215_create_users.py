"""create users table

Revision ID: 7dce4f9a21b1
Revises:
Create Date: 2026-11-20 02:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7dce4f9a21b1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("length(username) >= 3 AND length(username) <= 30", name="ck_users_username_length"),
        sa.CheckConstraint("length(display_name) >= 1 AND length(display_name) <= 80", name="ck_users_display_name_length"),
        sa.CheckConstraint("length(email) >= 3 AND length(email) <= 320", name="ck_users_email_length"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("CREATE UNIQUE INDEX uq_users_username_normalized ON users (LOWER(username))")
    op.execute("CREATE UNIQUE INDEX uq_users_email_normalized ON users (LOWER(email))")


def downgrade() -> None:
    op.drop_index("uq_users_email_normalized", table_name="users")
    op.drop_index("uq_users_username_normalized", table_name="users")
    op.drop_table("users")
