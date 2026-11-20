"""Rota publica de aceitacao de convites."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import get_settings
from app.core.auth_engine.auth_dependencies import get_auth_service
from app.core.auth_engine.auth_service import AuthService
from app.core.invite_engine.invite_schemas import AcceptInviteRequest
from app.core.invite_engine.invite_service import (
    InviteError,
    InviteExpiredError,
    InviteInvalidError,
    InviteRevokedError,
    InviteUsedError,
    InviteValidationError,
    InviteService,
)


router = APIRouter(prefix="/api/invites", tags=["invites"])


def validate_invite_origin(request: Request) -> None:
    settings = request.app.state.settings
    trusted = settings.get_trusted_origins() if hasattr(settings, "get_trusted_origins") else ()
    supplied = request.headers.get("origin")
    if not supplied:
        from urllib.parse import urlsplit

        referer = request.headers.get("referer")
        if referer:
            parsed = urlsplit(referer)
            supplied = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if not supplied or supplied.rstrip("/") not in trusted:
        raise HTTPException(status_code=403, detail="Origem nao autorizada")


@router.post("/accept")
def accept_invite(
    request: Request,
    response: Response,
    data: AcceptInviteRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    validate_invite_origin(request)
    settings = get_settings()
    service = InviteService(
        request.app.state.database,
        validity_hours=settings.invite_validity_hours,
        auth_service=auth_service,
    )
    try:
        user, session_token, csrf_token = service.accept_invite(data)
    except (InviteExpiredError, InviteRevokedError, InviteUsedError, InviteInvalidError, InviteValidationError):
        raise HTTPException(status_code=400, detail="Convite invalido ou indisponivel")
    except InviteError:
        raise HTTPException(status_code=400, detail="Nao foi possivel aceitar o convite")
    except Exception:
        raise HTTPException(status_code=500, detail="Nao foi possivel aceitar o convite")

    secure_cookie = settings.environment == "production"
    max_age = auth_service.session_duration_hours * 60 * 60
    response.set_cookie(
        "mestre_session",
        session_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        "mestre_csrf",
        csrf_token,
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
        },
        "csrf_token": csrf_token,
    }
