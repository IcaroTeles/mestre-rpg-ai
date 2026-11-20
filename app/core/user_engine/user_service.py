"""Regras de negocio para gerenciamento interno de usuarios."""

from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.database import DatabaseManager
from datetime import datetime, timezone

from app.core.database_models import User, UserSession
from app.core.user_engine.user_repository import UserRepository
from app.core.user_engine.user_schemas import (
    UserCreate,
    UserOutput,
    UserUpdate,
)


class UserConflictError(Exception):
    """Indica conflito de dados ou unicidade."""


class UserNotFoundError(Exception):
    """Indica que o usuario solicitado nao existe."""


class UserValidationError(Exception):
    """Indica dados invalidos fornecidos ao servico."""


class UserService:
    """Coordena validacao, repositorio e transacoes de usuarios."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create_in_session(self, session, data: UserCreate | dict) -> User:
        """Valida e cria um usuario usando a sessao fornecida."""

        try:
            data = UserCreate.model_validate(data)
        except ValidationError as exc:
            raise UserValidationError("Dados de usuario invalidos") from exc

        repository = UserRepository(session)
        if repository.get_by_username(data.username):
            raise UserConflictError("Nome de usuario ja esta em uso")
        if repository.get_by_email(data.email):
            raise UserConflictError("E-mail ja esta em uso")

        user = User(
            id=uuid4(),
            username=data.username,
            email=data.email,
            display_name=data.display_name,
            is_active=True,
        )
        repository.add(user)
        try:
            session.flush()
        except IntegrityError as exc:
            raise UserConflictError("Nome de usuario ou e-mail ja esta em uso") from exc
        return user

    def create(self, data: UserCreate | dict) -> UserOutput:
        try:
            data = UserCreate.model_validate(data)
        except ValidationError as exc:
            raise UserValidationError("Dados de usuario invalidos") from exc
        with self.database.transaction_scope() as session:
            repository = UserRepository(session)
            if repository.get_by_username(data.username):
                raise UserConflictError("Nome de usuario ja esta em uso")
            if repository.get_by_email(data.email):
                raise UserConflictError("E-mail ja esta em uso")

            user = User(
                id=uuid4(),
                username=data.username,
                email=data.email,
                display_name=data.display_name,
                is_active=True,
            )
            repository.add(user)
            try:
                session.flush()
            except IntegrityError as exc:
                session.rollback()
                raise UserConflictError("Nome de usuario ou e-mail ja esta em uso") from exc
            session.refresh(user)
            return UserOutput.model_validate(user)

    def get_by_id(self, user_id: UUID) -> UserOutput:
        with self.database.session_scope() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                raise UserNotFoundError("Usuario inexistente")
            return UserOutput.model_validate(user)

    def get_by_username(self, username: str) -> UserOutput:
        with self.database.session_scope() as session:
            user = UserRepository(session).get_by_username(username)
            if user is None:
                raise UserNotFoundError("Usuario inexistente")
            return UserOutput.model_validate(user)

    def get_by_email(self, email: str) -> UserOutput:
        with self.database.session_scope() as session:
            user = UserRepository(session).get_by_email(email)
            if user is None:
                raise UserNotFoundError("Usuario inexistente")
            return UserOutput.model_validate(user)

    def list(self, page: int = 1, page_size: int = 20) -> list[UserOutput]:
        if page < 1 or page_size < 1 or page_size > 100:
            raise UserValidationError("Parametros de paginacao invalidos")
        offset = (page - 1) * page_size
        with self.database.session_scope() as session:
            users = UserRepository(session).list(offset=offset, limit=page_size)
            return [UserOutput.model_validate(user) for user in users]

    def update(self, user_id: UUID, data: UserUpdate | dict) -> UserOutput:
        try:
            data = UserUpdate.model_validate(data)
        except ValidationError as exc:
            raise UserValidationError("Dados de usuario invalidos") from exc

        with self.database.transaction_scope() as session:
            repository = UserRepository(session)
            user = repository.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError("Usuario inexistente")

            if data.username is not None and data.username != user.username:
                conflict = repository.get_by_username(data.username)
                if conflict is not None and conflict.id != user.id:
                    raise UserConflictError("Nome de usuario ja esta em uso")
                user.username = data.username
            if data.email is not None and data.email != user.email:
                conflict = repository.get_by_email(data.email)
                if conflict is not None and conflict.id != user.id:
                    raise UserConflictError("E-mail ja esta em uso")
                user.email = data.email
            if data.display_name is not None:
                user.display_name = data.display_name

            try:
                session.flush()
            except IntegrityError as exc:
                session.rollback()
                raise UserConflictError("Nome de usuario ou e-mail ja esta em uso") from exc
            session.refresh(user)
            return UserOutput.model_validate(user)

    def deactivate(self, user_id: UUID) -> UserOutput:
        return self._set_active(user_id, False)

    def reactivate(self, user_id: UUID) -> UserOutput:
        return self._set_active(user_id, True)

    def _set_active(self, user_id: UUID, is_active: bool) -> UserOutput:
        with self.database.transaction_scope() as session:
            user = UserRepository(session).get_by_id(user_id)
            if user is None:
                raise UserNotFoundError("Usuario inexistente")
            user.is_active = is_active
            if not is_active:
                now = datetime.now(timezone.utc)
                sessions = session.query(UserSession).filter(
                    UserSession.user_id == user.id,
                    UserSession.revoked_at.is_(None),
                )
                sessions.update({UserSession.revoked_at: now}, synchronize_session=False)
            session.flush()
            session.refresh(user)
            return UserOutput.model_validate(user)
