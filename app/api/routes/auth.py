"""Endpoints internos de autenticacao por sessao persistente."""

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response

from app.core.auth_engine.auth_dependencies import get_authenticated_user, get_auth_service
from app.core.auth_engine.auth_schemas import AuthUser, LoginRequest, LoginResponse, SessionIdentity
from app.core.auth_engine.auth_service import (
    AuthService,
    InvalidCredentialsError,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_COOKIE = "mestre_session"
CSRF_COOKIE = "mestre_csrf"


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    expected = str(request.base_url).rstrip("/")
    if origin.rstrip("/") != expected:
        raise HTTPException(status_code=403, detail="Origem nao autorizada")


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    validate_origin(request)
    try:
        user = auth_service.authenticate(data.username_or_email, data.password)
        token, csrf_token, expires_at, _ = auth_service.create_session(user.id)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Credenciais invalidas")
    except Exception:
        raise HTTPException(status_code=500, detail="Nao foi possivel iniciar a sessao")

    secure_cookie = request.app.state.settings.environment == "production"
    max_age = auth_service.session_duration_hours * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    return LoginResponse(
        user=AuthUser.model_validate(user),
        csrf_token=csrf_token,
    )


@router.get("/me", response_model=SessionIdentity)
def me(
    request: Request,
    user: AuthUser = Depends(get_authenticated_user),
    mestre_csrf: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionIdentity:
    if not isinstance(mestre_csrf, str):
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    csrf_hash = getattr(request.state, "csrf_token_hash", "")
    if not auth_service.validate_csrf(csrf_hash, mestre_csrf):
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")

    return SessionIdentity(
        user=user,
        csrf_token=mestre_csrf,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    mestre_session: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    auth_service: AuthService = Depends(get_auth_service),
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    validate_origin(request)
    if mestre_session is None:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    csrf_hash = getattr(request.state, "csrf_token_hash", "")
    if not auth_service.validate_csrf(csrf_hash, x_csrf_token or ""):
        raise HTTPException(status_code=403, detail="Token CSRF invalido")
    auth_service.revoke_session(mestre_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "logged_out"}
