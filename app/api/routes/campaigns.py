"""Endpoints autenticados para criacao e gerenciamento de campanhas."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.auth_engine.auth_dependencies import get_authenticated_user, require_csrf
from app.core.auth_engine.auth_schemas import AuthUser
from app.core.campaign_engine.campaign_schemas import (
    CampaignAuditOutput,
    CampaignCreate,
    CampaignOutput,
    CampaignUpdate,
)
from app.core.campaign_engine.campaign_service import (
    CampaignError,
    CampaignForbiddenError,
    CampaignLimitReachedError,
    CampaignNotFoundError,
    CampaignOwnerError,
    CampaignService,
    CampaignStateError,
    CampaignValidationError,
)


router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def get_campaign_service(request: Request) -> CampaignService:
    settings = request.app.state.settings
    return CampaignService(
        request.app.state.database,
        max_campaigns_total=getattr(settings, "campaign_max_total", None),
    )


def campaign_error_response(exc: CampaignError) -> HTTPException:
    if isinstance(exc, CampaignNotFoundError):
        return HTTPException(status_code=404, detail="Campanha nao encontrada")
    if isinstance(exc, CampaignForbiddenError):
        return HTTPException(status_code=403, detail="Operacao nao autorizada")
    if isinstance(exc, CampaignOwnerError):
        return HTTPException(status_code=403, detail="Owner inexistente ou inativo")
    if isinstance(exc, CampaignStateError):
        return HTTPException(status_code=409, detail="Transicao de campanha invalida")
    if isinstance(exc, CampaignValidationError):
        return HTTPException(status_code=422, detail="Dados da campanha invalidos")
    if isinstance(exc, CampaignLimitReachedError):
        return HTTPException(status_code=503, detail="Limite tecnico de campanhas atingido")
    return HTTPException(status_code=500, detail="Erro interno do servidor")


@router.post(
    "",
    response_model=CampaignOutput,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    data: CampaignCreate,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    try:
        return CampaignOutput.model_validate(service.create(user.id, data))
    except CampaignError as exc:
        raise campaign_error_response(exc) from exc


@router.get("", response_model=list[CampaignOutput])
def list_campaigns(
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
) -> list[CampaignOutput]:
    return service.list_owned(user.id)


@router.get("/{campaign_id}", response_model=CampaignOutput)
def get_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
) -> CampaignOutput:
    try:
        return service.get(user.id, campaign_id)
    except CampaignError as exc:
        raise campaign_error_response(exc) from exc


@router.patch("/{campaign_id}", response_model=CampaignOutput)
def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    try:
        return service.update(user.id, campaign_id, data)
    except CampaignError as exc:
        raise campaign_error_response(exc) from exc


def _transition(
    action: str,
    campaign_id: UUID,
    service: CampaignService,
    user: AuthUser,
) -> CampaignOutput:
    try:
        return service.transition(user.id, campaign_id, action)
    except CampaignError as exc:
        raise campaign_error_response(exc) from exc


@router.post("/{campaign_id}/start", response_model=CampaignOutput)
def start_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    return _transition("start", campaign_id, service, user)


@router.post("/{campaign_id}/pause", response_model=CampaignOutput)
def pause_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    return _transition("pause", campaign_id, service, user)


@router.post("/{campaign_id}/resume", response_model=CampaignOutput)
def resume_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    return _transition("resume", campaign_id, service, user)


@router.post("/{campaign_id}/end", response_model=CampaignOutput)
def end_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    return _transition("end", campaign_id, service, user)


@router.post("/{campaign_id}/reopen", response_model=CampaignOutput)
def reopen_campaign(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
    _: None = Depends(require_csrf),
) -> CampaignOutput:
    return _transition("reopen", campaign_id, service, user)


@router.get(
    "/{campaign_id}/audit",
    response_model=list[CampaignAuditOutput],
)
def list_campaign_audit(
    campaign_id: UUID,
    service: CampaignService = Depends(get_campaign_service),
    user: AuthUser = Depends(get_authenticated_user),
) -> list[CampaignAuditOutput]:
    try:
        return service.list_audit_events(user.id, campaign_id)
    except CampaignError as exc:
        raise campaign_error_response(exc) from exc
