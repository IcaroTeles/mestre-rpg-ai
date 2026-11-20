"""Base compartilhada e modelos persistentes da aplicacao."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, text, true
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base vazia para evolucao segura das futuras entidades."""


class User(Base):
    """Representa uma conta de usuario sem dados de autenticacao."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("uq_users_username_normalized", text("lower(username)"), unique=True),
        Index("uq_users_email_normalized", text("lower(email)"), unique=True),
        CheckConstraint("length(username) >= 3 AND length(username) <= 30", name="ck_users_username_length"),
        CheckConstraint("length(display_name) >= 1 AND length(display_name) <= 80", name="ck_users_display_name_length"),
        CheckConstraint("length(email) >= 3 AND length(email) <= 320", name="ck_users_email_length"),
    )


class UserSession(Base):
    """Sessao persistente ligada a um usuario."""

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("uq_user_sessions_token_hash", token_hash, unique=True),
        Index("ix_user_sessions_user_id", user_id),
    )
