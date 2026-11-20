"""Operacoes SQLAlchemy para usuarios."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database_models import User


class UserRepository:
    """Acesso persistente sem regras de interface."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: User) -> User:
        self.session.add(user)
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.scalar(select(User).where(User.id == user_id))

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.username == username.strip().lower())
        )

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.email == email.strip().lower())
        )

    def list(self, offset: int, limit: int) -> list[User]:
        statement = select(User).order_by(User.created_at, User.id).offset(offset).limit(limit)
        return list(self.session.scalars(statement))
