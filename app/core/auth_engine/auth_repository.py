"""Repositorio de sessoes persistentes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database_models import User, UserSession


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user_by_username_or_email(self, value: str) -> User | None:
        normalized = value.strip().lower()
        return self.session.scalar(
            select(User).where(
                (User.username == normalized) | (User.email == normalized)
            )
        )

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.session.scalar(select(User).where(User.id == user_id))

    def get_session_by_token_hash(self, token_hash: str) -> UserSession | None:
        return self.session.scalar(
            select(UserSession).where(UserSession.token_hash == token_hash)
        )

    def add_session(self, session_record: UserSession) -> UserSession:
        self.session.add(session_record)
        return session_record

    def revoke_session(self, session_record: UserSession, now: datetime) -> None:
        if session_record.revoked_at is None:
            session_record.revoked_at = now

    def revoke_all_user_sessions(self, user_id: UUID, now: datetime) -> None:
        sessions = self.session.scalars(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        )
        for session_record in sessions:
            session_record.revoked_at = now
