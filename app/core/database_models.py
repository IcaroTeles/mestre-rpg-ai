"""Base compartilhada e modelos persistentes da aplicacao."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.orm import DeclarativeBase

from app.core.campaign_engine.campaign_types import (
    CampaignDuration,
    CampaignFrequency,
    CampaignStatus,
)


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


class UserInvite(Base):
    """Convite individual e de uso unico para ingresso de jogador."""

    __tablename__ = "user_invites"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    used_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="player")
    campaign_id: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("uq_user_invites_token_hash", token_hash, unique=True),
        Index("ix_user_invites_created_by_user_id", created_by_user_id),
        Index("ix_user_invites_used_by_user_id", used_by_user_id),
        Index("ix_user_invites_expires_at", expires_at),
        CheckConstraint("purpose = 'player'", name="ck_user_invites_player_purpose"),
    )


class Campaign(Base):
    """Campanha persistente com um unico Owner."""

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        SqlEnum(
            CampaignStatus,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
            create_constraint=True,
            name="ck_campaigns_status",
        ),
        nullable=False,
        default=CampaignStatus.PREPARATION,
        server_default=CampaignStatus.PREPARATION.value,
    )
    duration_category: Mapped[CampaignDuration] = mapped_column(
        SqlEnum(
            CampaignDuration,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
            create_constraint=True,
            name="ck_campaigns_duration_category",
        ),
        nullable=False,
    )
    planned_session_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=180,
        server_default="180",
    )
    frequency: Mapped[CampaignFrequency] = mapped_column(
        SqlEnum(
            CampaignFrequency,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
            create_constraint=True,
            name="ck_campaigns_frequency",
        ),
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
        CheckConstraint(
            "length(name) >= 1 AND length(name) <= 100",
            name="ck_campaigns_name_length",
        ),
        CheckConstraint(
            "planned_session_duration_minutes >= 120 "
            "AND planned_session_duration_minutes <= 240",
            name="ck_campaigns_session_duration",
        ),
        CheckConstraint(
            "start_date IS NULL OR estimated_completion_date IS NULL "
            "OR estimated_completion_date >= start_date",
            name="ck_campaigns_completion_date",
        ),
        Index("ix_campaigns_owner_user_id", owner_user_id),
        Index("ix_campaigns_status", status),
    )


class CampaignAuditEvent(Base):
    """Evento de auditoria ligado a uma campanha e ao autor da operacao."""

    __tablename__ = "campaign_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_campaign_audit_events_campaign_id", campaign_id),
        Index("ix_campaign_audit_events_actor_user_id", actor_user_id),
        Index("ix_campaign_audit_events_created_at", created_at),
    )
