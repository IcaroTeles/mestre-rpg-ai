"""Regras de negocio, propriedade e ciclo de vida de campanhas."""

import logging
from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.core.campaign_engine.campaign_repository import CampaignRepository
from app.core.campaign_engine.campaign_schemas import (
    CampaignAuditOutput,
    CampaignCreate,
    CampaignOutput,
    CampaignUpdate,
)
from app.core.campaign_engine.campaign_types import CampaignStatus
from app.core.database import DatabaseManager
from app.core.database_models import Campaign, CampaignAuditEvent, User


logger = logging.getLogger("mestre_rpg")


class CampaignError(Exception):
    """Erro base das regras de campanhas."""


class CampaignNotFoundError(CampaignError):
    """Campanha inexistente."""


class CampaignForbiddenError(CampaignError):
    """Operacao solicitada por alguem que nao e Owner."""


class CampaignStateError(CampaignError):
    """Transicao de estado invalida."""


class CampaignValidationError(CampaignError):
    """Dados de campanha invalidos."""


class CampaignOwnerError(CampaignError):
    """Owner inexistente ou inativo."""


class CampaignLimitReachedError(CampaignError):
    """Limite tecnico global de campanhas alcancado."""


class CampaignService:
    def __init__(
        self,
        database: DatabaseManager,
        max_campaigns_total: int | None = None,
    ) -> None:
        self.database = database
        self.max_campaigns_total = max_campaigns_total

    def create(
        self,
        owner_user_id: UUID,
        data: CampaignCreate | dict,
    ) -> CampaignOutput:
        try:
            campaign_data = CampaignCreate.model_validate(data)
        except ValidationError as exc:
            raise CampaignValidationError("Dados da campanha invalidos") from exc

        with self.database.transaction_scope() as session:
            owner = session.get(User, owner_user_id)
            if owner is None or not owner.is_active:
                raise CampaignOwnerError("Owner inexistente ou inativo")

            repository = CampaignRepository(session)
            if (
                self.max_campaigns_total is not None
                and repository.count_all() >= self.max_campaigns_total
            ):
                raise CampaignLimitReachedError("Limite global de campanhas alcancado")

            campaign = Campaign(
                id=uuid4(),
                name=campaign_data.name,
                description=campaign_data.description,
                owner_user_id=owner_user_id,
                status=CampaignStatus.PREPARATION,
                duration_category=campaign_data.duration_category,
                planned_session_duration_minutes=campaign_data.planned_session_duration_minutes,
                frequency=campaign_data.frequency,
                start_date=campaign_data.start_date,
                estimated_completion_date=campaign_data.estimated_completion_date,
            )
            repository.add(campaign)
            repository.add_audit_event(
                CampaignAuditEvent(
                    id=uuid4(),
                    campaign_id=campaign.id,
                    actor_user_id=owner_user_id,
                    action="created",
                    details={
                        "name": campaign.name,
                        "description": campaign.description,
                        "duration_category": campaign.duration_category.value,
                        "planned_session_duration_minutes": campaign.planned_session_duration_minutes,
                        "frequency": campaign.frequency.value,
                        "start_date": (
                            campaign.start_date.isoformat()
                            if campaign.start_date is not None
                            else None
                        ),
                        "estimated_completion_date": (
                            campaign.estimated_completion_date.isoformat()
                            if campaign.estimated_completion_date is not None
                            else None
                        ),
                    },
                )
            )
            session.flush()
            return CampaignOutput.model_validate(campaign)

    def list_owned(self, actor_user_id: UUID) -> list[CampaignOutput]:
        with self.database.session_scope() as session:
            campaigns = CampaignRepository(session).list_by_owner(actor_user_id)
            return [CampaignOutput.model_validate(campaign) for campaign in campaigns]

    def get(self, actor_user_id: UUID, campaign_id: UUID) -> CampaignOutput:
        with self.database.session_scope() as session:
            repository = CampaignRepository(session)
            campaign = self._require_owner(
                repository.get_by_id(campaign_id),
                actor_user_id,
                "consult",
            )
            return CampaignOutput.model_validate(campaign)

    def update(
        self,
        actor_user_id: UUID,
        campaign_id: UUID,
        data: CampaignUpdate | dict,
    ) -> CampaignOutput:
        try:
            update_data = CampaignUpdate.model_validate(data)
        except ValidationError as exc:
            raise CampaignValidationError("Dados da campanha invalidos") from exc

        with self.database.transaction_scope() as session:
            repository = CampaignRepository(session)
            campaign = self._require_owner(
                repository.get_by_id(campaign_id),
                actor_user_id,
                "update",
            )
            if campaign.status == CampaignStatus.ENDED:
                raise CampaignStateError("Campanha encerrada nao pode ser alterada")

            changes = update_data.model_dump(exclude_unset=True)
            proposed_start_date = changes.get("start_date", campaign.start_date)
            proposed_completion_date = changes.get(
                "estimated_completion_date",
                campaign.estimated_completion_date,
            )
            if (
                proposed_start_date is not None
                and proposed_completion_date is not None
                and proposed_completion_date < proposed_start_date
            ):
                raise CampaignValidationError(
                    "A previsao de conclusao deve ser posterior ao inicio"
                )

            for field_name, new_value in changes.items():
                old_value = getattr(campaign, field_name)
                if old_value == new_value:
                    continue
                setattr(campaign, field_name, new_value)
                audit_action = (
                    "duration_category_changed"
                    if field_name == "duration_category"
                    else "field_updated"
                )
                repository.add_audit_event(
                    CampaignAuditEvent(
                        id=uuid4(),
                        campaign_id=campaign.id,
                        actor_user_id=actor_user_id,
                        action=audit_action,
                        details={
                            "field": field_name,
                            "from": self._audit_value(old_value),
                            "to": self._audit_value(new_value),
                        },
                    )
                )

            session.flush()
            return CampaignOutput.model_validate(campaign)

    def transition(
        self,
        actor_user_id: UUID,
        campaign_id: UUID,
        action: str,
    ) -> CampaignOutput:
        transitions = {
            "start": (CampaignStatus.PREPARATION, CampaignStatus.ACTIVE),
            "pause": (CampaignStatus.ACTIVE, CampaignStatus.PAUSED),
            "resume": (CampaignStatus.PAUSED, CampaignStatus.ACTIVE),
            "end": (
                (
                    CampaignStatus.PREPARATION,
                    CampaignStatus.ACTIVE,
                    CampaignStatus.PAUSED,
                ),
                CampaignStatus.ENDED,
            ),
            "reopen": (CampaignStatus.ENDED, CampaignStatus.PREPARATION),
        }
        transition = transitions.get(action)
        if transition is None:
            raise CampaignStateError("Acao de campanha invalida")

        with self.database.transaction_scope() as session:
            repository = CampaignRepository(session)
            campaign = self._require_owner(
                repository.get_by_id(campaign_id),
                actor_user_id,
                action,
            )
            expected, target = transition
            if isinstance(expected, tuple):
                is_valid = campaign.status in expected
            else:
                is_valid = campaign.status == expected
            if not is_valid:
                raise CampaignStateError("Transicao de estado invalida")

            previous_status = campaign.status
            campaign.status = target
            repository.add_audit_event(
                CampaignAuditEvent(
                    id=uuid4(),
                    campaign_id=campaign.id,
                    actor_user_id=actor_user_id,
                    action="reopened" if action == "reopen" else "state_changed",
                    details={
                        "operation": action,
                        "from": previous_status.value,
                        "to": target.value,
                    },
                )
            )
            session.flush()
            return CampaignOutput.model_validate(campaign)

    def list_audit_events(
        self,
        actor_user_id: UUID,
        campaign_id: UUID,
    ) -> list[CampaignAuditOutput]:
        with self.database.session_scope() as session:
            repository = CampaignRepository(session)
            campaign = self._require_owner(
                repository.get_by_id(campaign_id),
                actor_user_id,
                "consult audit",
            )
            events = repository.list_audit_events(campaign_id)
            return [CampaignAuditOutput.model_validate(event) for event in events]

    @staticmethod
    def _require_owner(
        campaign: Campaign | None,
        actor_user_id: UUID,
        operation: str,
    ) -> Campaign:
        if campaign is None:
            raise CampaignNotFoundError("Campanha inexistente")
        if campaign.owner_user_id != actor_user_id:
            logger.warning(
                "Operacao de campanha nao autorizada: campaign_id=%s actor_user_id=%s operation=%s",
                campaign.id,
                actor_user_id,
                operation,
            )
            raise CampaignForbiddenError("Somente o Owner pode realizar esta operacao")
        return campaign

    @staticmethod
    def _audit_value(value: object) -> str | int | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, StrEnum):
            return value.value
        if isinstance(value, int):
            return value
        return str(value)
