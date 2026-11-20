"""Dependencias FastAPI reutilizaveis para autenticacao."""

from urllib.parse import urlsplit

from fastapi import Cookie, Depends, Header, HTTPException, Request

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


def validate_origin(request: Request) -> None:
    settings = request.app.state.settings
    get_trusted_origins = getattr(settings, "get_trusted_origins", None)
    if callable(get_trusted_origins):
        trusted_origins = get_trusted_origins()
    else:
        trusted_origins = (
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            str(request.base_url).rstrip("/"),
        )

    supplied = request.headers.get("origin")
    if supplied is None:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlsplit(referer)
            supplied = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if not supplied or supplied.rstrip("/") not in trusted_origins:
        raise HTTPException(status_code=403, detail="Origem nao autorizada")


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    user: AuthUser = Depends(get_authenticated_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    del user
    validate_origin(request)
    csrf_hash = getattr(request.state, "csrf_token_hash", "")
    if not auth_service.validate_csrf(csrf_hash, x_csrf_token or ""):
        raise HTTPException(status_code=403, detail="Token CSRF invalido")
