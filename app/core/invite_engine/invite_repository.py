"""Operacoes SQLAlchemy para convites."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database_models import UserInvite


class InviteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, invite: UserInvite) -> UserInvite:
        self.session.add(invite)
        return invite

    def get_by_id(self, invite_id: UUID) -> UserInvite | None:
        return self.session.scalar(
            select(UserInvite).where(UserInvite.id == invite_id)
        )

    def get_by_token_hash(self, token_hash: str) -> UserInvite | None:
        return self.session.scalar(
            select(UserInvite).where(UserInvite.token_hash == token_hash)
        )

    def list(self, offset: int, limit: int) -> list[UserInvite]:
        statement = (
            select(UserInvite)
            .order_by(UserInvite.created_at.desc(), UserInvite.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def revoke(self, invite: UserInvite, now: datetime) -> None:
        if invite.revoked_at is None:
            invite.revoked_at = now
