"""Servico de autenticacao, hashes e sessoes persistentes."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from pwdlib import PasswordHash
from functools import lru_cache

from app.core.auth_engine.auth_repository import AuthRepository
from app.core.database import DatabaseManager
from app.core.database_models import User, UserSession


class AuthError(Exception):
    pass


class InvalidCredentialsError(AuthError):
    pass


class SessionInvalidError(AuthError):
    pass


class SessionExpiredError(AuthError):
    pass


class SessionRevokedError(AuthError):
    pass


class PasswordValidationError(AuthError):
    pass


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHash:
    return PasswordHash.recommended()


@lru_cache(maxsize=1)
def get_dummy_password_hash() -> str:
    return get_password_hasher().hash(
        "Dummy-Argon2-Password-For-Timing-Only-2.3"
    )


class AuthService:
    def __init__(self, database: DatabaseManager, session_duration_hours: int = 12) -> None:
        self.database = database
        self.session_duration_hours = session_duration_hours
        self.password_hasher = get_password_hasher()
        self.dummy_password_hash = get_dummy_password_hash()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def set_password(self, user_id: UUID, password: str) -> None:
        if (
            not isinstance(password, str)
            or not password.strip()
            or len(password) < 12
            or len(password) > 128
        ):
            raise PasswordValidationError("Senha invalida")

        password_hash = self.password_hasher.hash(password)
        now = datetime.now(timezone.utc)
        with self.database.transaction_scope() as session:
            repository = AuthRepository(session)
            user = repository.get_user_by_id(user_id)
            if user is None:
                raise AuthError("Usuario inexistente")
            user.password_hash = password_hash
            repository.revoke_all_user_sessions(user_id, now)

    def set_password_in_session(self, session, user: User, password: str) -> None:
        """Define o hash Argon2id usando uma sessao existente."""

        if (
            not isinstance(password, str)
            or not password.strip()
            or len(password) < 12
            or len(password) > 128
        ):
            raise PasswordValidationError("Senha invalida")
        user.password_hash = self.password_hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self.password_hasher.verify(password, password_hash)
        except Exception:
            return False

    def authenticate(self, username_or_email: str, password: str) -> User:
        with self.database.transaction_scope() as session:
            user = AuthRepository(session).get_user_by_username_or_email(username_or_email)
            if user is None or not user.is_active or not user.password_hash:
                self.password_hasher.verify(password, self.dummy_password_hash)
                raise InvalidCredentialsError("Credenciais invalidas")
            try:
                verified, updated_hash = self.password_hasher.verify_and_update(
                    password,
                    user.password_hash,
                )
            except Exception:
                verified = False
                updated_hash = None
            if not verified:
                raise InvalidCredentialsError("Credenciais invalidas")
            if updated_hash is not None:
                user.password_hash = updated_hash
            session.expunge(user)
            return user

    def create_session(self, user_id: UUID) -> tuple[str, str, datetime, UUID]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.session_duration_hours)
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)

        with self.database.transaction_scope() as session:
            repository = AuthRepository(session)
            user = repository.get_user_by_id(user_id)
            if user is None:
                raise AuthError("Usuario inexistente")
            if not user.is_active:
                raise AuthError("Usuario inativo")

            session_record = UserSession(
                id=uuid4(),
                user_id=user_id,
                token_hash=self._hash_token(token),
                csrf_token_hash=self._hash_token(csrf_token),
                created_at=now,
                expires_at=expires_at,
                revoked_at=None,
            )
            repository.add_session(session_record)
            session.flush()
            return token, csrf_token, expires_at, session_record.id

    def get_session(self, token: str) -> tuple[User, str]:
        if not token:
            raise SessionInvalidError("Sessao invalida")

        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        with self.database.session_scope() as session:
            repository = AuthRepository(session)
            session_record = repository.get_session_by_token_hash(token_hash)
            if session_record is None:
                raise SessionInvalidError("Sessao invalida")
            if session_record.revoked_at is not None:
                raise SessionRevokedError("Sessao revogada")

            expires_at = session_record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise SessionExpiredError("Sessao expirada")

            user = repository.get_user_by_id(session_record.user_id)
            if user is None or not user.is_active:
                raise SessionInvalidError("Sessao invalida")

            session.expunge(user)
            return user, session_record.csrf_token_hash

    def validate_csrf(self, token: str, csrf_token: str) -> bool:
        if not csrf_token:
            return False
        return secrets.compare_digest(self._hash_token(csrf_token), token)

    def revoke_session(self, token: str) -> None:
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        with self.database.transaction_scope() as session:
            repository = AuthRepository(session)
            session_record = repository.get_session_by_token_hash(token_hash)
            if session_record is None:
                raise SessionInvalidError("Sessao invalida")
            repository.revoke_session(session_record, now)

    def revoke_all_user_sessions(self, user_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        with self.database.transaction_scope() as session:
            AuthRepository(session).revoke_all_user_sessions(user_id, now)
