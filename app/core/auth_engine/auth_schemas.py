"""Schemas da autenticacao sem dados sensiveis."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username_or_email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    display_name: str
    is_active: bool


class LoginResponse(BaseModel):
    user: AuthUser
    csrf_token: str


class SessionIdentity(BaseModel):
    user: AuthUser
    csrf_token: str
