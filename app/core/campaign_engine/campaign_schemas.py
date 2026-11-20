"""Schemas de entrada e saida para campanhas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.campaign_engine.campaign_types import (
    CampaignDuration,
    CampaignFrequency,
    CampaignStatus,
)


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    duration_category: CampaignDuration
    planned_session_duration_minutes: int = Field(default=180, ge=120, le=240)
    frequency: CampaignFrequency
    start_date: date | None = None
    estimated_completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome da campanha nao pode ser vazio")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_dates(self) -> "CampaignCreate":
        if (
            self.start_date is not None
            and self.estimated_completion_date is not None
            and self.estimated_completion_date < self.start_date
        ):
            raise ValueError("A previsao de conclusao deve ser posterior ao inicio")
        return self


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    duration_category: CampaignDuration | None = None
    planned_session_duration_minutes: int | None = Field(
        default=None,
        ge=120,
        le=240,
    )
    frequency: CampaignFrequency | None = None
    start_date: date | None = None
    estimated_completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome da campanha nao pode ser vazio")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_changes(self) -> "CampaignUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        for field_name in (
            "name",
            "duration_category",
            "planned_session_duration_minutes",
            "frequency",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"O campo {field_name} nao pode ser nulo")
        return self


class CampaignOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    owner_user_id: UUID
    status: CampaignStatus
    duration_category: CampaignDuration
    planned_session_duration_minutes: int
    frequency: CampaignFrequency
    start_date: date | None
    estimated_completion_date: date | None
    created_at: datetime
    updated_at: datetime


class CampaignAuditOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    actor_user_id: UUID
    action: str
    details: dict
    created_at: datetime
