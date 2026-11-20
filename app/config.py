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

    @property
    def ollama_api_url(self) -> str:
        return self.ollama_url.rstrip("/")


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
