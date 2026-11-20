"""Schemas de convites e aceite."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.user_engine.user_schemas import normalize_email, normalize_username


class InviteOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    created_by_user_id: UUID
    used_by_user_id: UUID | None
    purpose: str
    campaign_id: UUID | None


class CreatedInviteOutput(BaseModel):
    invite: InviteOutput
    token: str


class AcceptInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=128)
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=320)
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)

    _username_normalizer = field_validator("username")(normalize_username)
    _email_normalizer = field_validator("email")(normalize_email)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome de exibicao nao pode ser vazio")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Senha invalida")
        return value
