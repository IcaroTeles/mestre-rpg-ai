"""Dependencias FastAPI reutilizaveis para autenticacao."""

from fastapi import Cookie, Depends, HTTPException, Request

from app.core.auth_engine.auth_schemas import AuthUser
from app.core.auth_engine.auth_service import (
    AuthService,
    SessionExpiredError,
    SessionInvalidError,
    SessionRevokedError,
)


def get_auth_service(request: Request) -> AuthService:
    from app.config import get_settings

    return AuthService(
        request.app.state.database,
        get_settings().session_duration_hours,
    )


def get_authenticated_user(
    request: Request,
    mestre_session: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    if mestre_session is None:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    try:
        user, csrf_hash = auth_service.get_session(mestre_session)
    except (SessionExpiredError, SessionRevokedError, SessionInvalidError):
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    request.state.csrf_token_hash = csrf_hash
    return AuthUser.model_validate(user)
