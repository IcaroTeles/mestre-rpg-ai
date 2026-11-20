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
    bind = op.get_bind()
    duplicate_username = bind.exec_driver_sql(
        "SELECT LOWER(username) FROM users "
        "GROUP BY LOWER(username) HAVING COUNT(*) > 1 LIMIT 1"
    ).first()
    if duplicate_username is not None:
        raise RuntimeError("Migracao interrompida: usernames preexistentes divergem apenas por maiusculas/minusculas")

    duplicate_email = bind.exec_driver_sql(
        "SELECT LOWER(email) FROM users "
        "GROUP BY LOWER(email) HAVING COUNT(*) > 1 LIMIT 1"
    ).first()
    if duplicate_email is not None:
        raise RuntimeError("Migracao interrompida: emails preexistentes divergem apenas por maiusculas/minusculas")

    op.execute("DROP INDEX IF EXISTS uq_users_username_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_email_normalized")
    op.execute("CREATE UNIQUE INDEX uq_users_username_normalized ON users (LOWER(username))")
    op.execute("CREATE UNIQUE INDEX uq_users_email_normalized ON users (LOWER(email))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_username_normalized")
    op.execute("DROP INDEX IF EXISTS uq_users_email_normalized")
    op.create_index("uq_users_username_normalized", "users", ["username"], unique=True)
    op.create_index("uq_users_email_normalized", "users", ["email"], unique=True)
