"""Configuracoes centralizadas da aplicacao."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuracoes carregadas por variaveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mestre RPG AI"
    app_version: str = "1.0.0"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:12b"
    ollama_timeout: float = Field(default=5.0, gt=0)

    data_dir: Path = PROJECT_ROOT / "data"
    campaigns_dir: Path = PROJECT_ROOT / "data" / "campaigns"
    knowledge_base_dir: Path = PROJECT_ROOT / "data" / "knowledge_base"
    uploads_dir: Path = PROJECT_ROOT / "data" / "uploads"
    log_dir: Path = PROJECT_ROOT / "data" / "logs"
    database_dir: Path = PROJECT_ROOT / "data"
    database_filename: str = "mestre_rpg.db"
    database_url: str | None = None
    session_duration_hours: int = Field(default=12, ge=1, le=24 * 30)
    trusted_origins: str = ""
    invite_validity_hours: int = Field(default=48, ge=1, le=24 * 30)

    def get_trusted_origins(self) -> tuple[str, ...]:
        configured = [
            origin.strip().rstrip("/")
            for origin in self.trusted_origins.split(",")
            if origin.strip()
        ]
        if self.environment == "development":
            configured.extend(
                [
                    "http://127.0.0.1:8000",
                    "http://localhost:8000",
                ]
            )
        return tuple(dict.fromkeys(origin for origin in configured if origin))

    @property
    def ollama_api_url(self) -> str:
        return self.ollama_url.rstrip("/")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        self.database_dir.mkdir(parents=True, exist_ok=True)
        database_path = (self.database_dir / self.database_filename).resolve()
        return f"sqlite:///{database_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """Retorna uma unica instancia de configuracoes."""

    settings = Settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    for directory in (
        settings.data_dir,
        settings.campaigns_dir,
        settings.knowledge_base_dir,
        settings.uploads_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
