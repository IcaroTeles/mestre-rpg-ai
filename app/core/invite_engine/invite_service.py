"""Regras de negocio e ciclo de vida dos convites."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.auth_engine.auth_service import AuthService
from app.core.database import DatabaseManager
from app.core.database_models import User, UserInvite
from app.core.invite_engine.invite_repository import InviteRepository
from app.core.invite_engine.invite_schemas import (
    AcceptInviteRequest,
    CreatedInviteOutput,
    InviteOutput,
)
from app.core.user_engine.user_repository import UserRepository
from app.core.user_engine.user_schemas import UserCreate, UserOutput


class InviteError(Exception):
    pass


class InviteUnauthorizedError(InviteError):
    pass


class InviteInvalidError(InviteError):
    pass


class InviteExpiredError(InviteError):
    pass


class InviteRevokedError(InviteError):
    pass


class InviteUsedError(InviteError):
    pass


class InviteValidationError(InviteError):
    pass


class InviteService:
    def __init__(
        self,
        database: DatabaseManager,
        validity_hours: int = 48,
        auth_service: AuthService | None = None,
    ) -> None:
        self.database = database
        self.validity_hours = validity_hours
        self.auth_service = auth_service or AuthService(database)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_invite(
        self,
        created_by_user_id: UUID,
        authorized_as_administrator: bool = False,
        validity_hours: int | None = None,
        campaign_id: UUID | None = None,
    ) -> CreatedInviteOutput:
        if not authorized_as_administrator:
            raise InviteUnauthorizedError("Operacao nao autorizada")

        duration = validity_hours if validity_hours is not None else self.validity_hours
        if duration < 1 or duration > 24 * 30:
            raise InviteValidationError("Validade invalida")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration)
        token = secrets.token_urlsafe(32)

        with self.database.transaction_scope() as session:
            creator = session.get(User, created_by_user_id)
            if creator is None or not creator.is_active:
                raise InviteUnauthorizedError("Criador nao autorizado")

            invite = UserInvite(
                id=uuid4(),
                token_hash=self.hash_token(token),
                created_at=now,
                expires_at=expires_at,
                used_at=None,
                revoked_at=None,
                created_by_user_id=created_by_user_id,
                used_by_user_id=None,
                purpose="player",
                campaign_id=campaign_id,
            )
            InviteRepository(session).add(invite)
            session.flush()
            return CreatedInviteOutput(
                invite=InviteOutput.model_validate(invite),
                token=token,
            )

    def list_invites(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> list[InviteOutput]:
        if page < 1 or page_size < 1 or page_size > 100:
            raise InviteValidationError("Parametros de paginacao invalidos")
        offset = (page - 1) * page_size
        with self.database.session_scope() as session:
            invites = InviteRepository(session).list(offset, page_size)
            return [InviteOutput.model_validate(invite) for invite in invites]

    def revoke_invite(self, invite_id: UUID) -> InviteOutput:
        now = datetime.now(timezone.utc)
        with self.database.transaction_scope() as session:
            invite = InviteRepository(session).get_by_id(invite_id)
            if invite is None:
                raise InviteInvalidError("Convite inexistente")
            if invite.used_at is not None:
                raise InviteUsedError("Convite ja utilizado")
            if invite.revoked_at is not None:
                return InviteOutput.model_validate(invite)
            InviteRepository(session).revoke(invite, now)
            session.flush()
            return InviteOutput.model_validate(invite)

    def accept_invite(
        self,
        data: AcceptInviteRequest,
    ) -> tuple[UserOutput, str, str]:
        try:
            data = AcceptInviteRequest.model_validate(data.model_dump())
        except ValidationError as exc:
            raise InviteValidationError("Dados de cadastro invalidos") from exc

        now = datetime.now(timezone.utc)
        now_for_sqlite = now.replace(tzinfo=None)
        token_hash = self.hash_token(data.token)

        with self.database.transaction_scope() as session:
            invite = InviteRepository(session).get_by_token_hash(token_hash)
            if invite is None:
                raise InviteInvalidError("Convite invalido")
            if invite.revoked_at is not None:
                raise InviteRevokedError("Convite revogado")
            if invite.used_at is not None:
                raise InviteUsedError("Convite ja utilizado")

            expires_at = invite.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise InviteExpiredError("Convite expirado")

            user_repository = UserRepository(session)
            if user_repository.get_by_username(data.username):
                raise InviteInvalidError("Dados de cadastro invalidos")
            if user_repository.get_by_email(data.email):
                raise InviteInvalidError("Dados de cadastro invalidos")

            user = User(
                id=uuid4(),
                username=data.username,
                email=data.email,
                display_name=data.display_name,
                is_active=True,
            )
            user_repository.add(user)
            try:
                session.flush()
            except IntegrityError as exc:
                raise InviteInvalidError("Dados de cadastro invalidos") from exc

            user.password_hash = self.auth_service.password_hasher.hash(data.password)

            result = session.execute(
                update(UserInvite)
                .where(
                    UserInvite.id == invite.id,
                    UserInvite.used_at.is_(None),
                    UserInvite.revoked_at.is_(None),
                    UserInvite.expires_at > now_for_sqlite,
                )
                .values(
                    used_at=now,
                    used_by_user_id=user.id,
                )
            )
            if result.rowcount != 1:
                raise InviteUsedError("Convite ja utilizado")

            session.flush()
            output = UserOutput.model_validate(user)

        token, csrf_token, _, _ = self.auth_service.create_session(output.id)
        return output, token, csrf_token
