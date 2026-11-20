"""Schemas Pydantic para validacao de usuarios."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Validacao basica: nao garante conformidade RFC completa nem existencia da caixa.


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "O nome de usuario deve ter 3 a 30 caracteres e usar letras, "
            "numeros, ponto, hifen ou sublinhado"
        )
    return normalized


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Formato de e-mail invalido")
    return normalized


class UserCreate(BaseModel):
    """Dados necessarios para criar uma conta."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=320)
    display_name: str = Field(min_length=1, max_length=80)

    _username_normalizer = field_validator("username")(normalize_username)
    _email_normalizer = field_validator("email")(normalize_email)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome de exibicao nao pode ser vazio")
        return normalized


class UserUpdate(BaseModel):
    """Dados permitidos em uma atualizacao."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=3, max_length=30)
    email: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("username")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_username(value)

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome de exibicao nao pode ser vazio")
        return normalized


class UserOutput(BaseModel):
    """Representacao segura de usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
