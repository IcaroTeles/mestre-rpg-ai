"""make user uniqueness case-insensitive

Revision ID: 8e1a4b2c53d7
Revises: 7dce4f9a21b1
Create Date: 2026-11-20 02:35:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "8e1a4b2c53d7"
down_revision: Union[str, Sequence[str], None] = "7dce4f9a21b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_username_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_email_normalized")
    op.execute("CREATE UNIQUE INDEX uq_users_username_normalized ON users (LOWER(username))")
    op.execute("CREATE UNIQUE INDEX uq_users_email_normalized ON users (LOWER(email))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_username_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_email_normalized")
    op.create_index("uq_users_username_normalized", "users", ["username"], unique=True)
    op.create_index("uq_users_email_normalized", "users", ["email"], unique=True)
