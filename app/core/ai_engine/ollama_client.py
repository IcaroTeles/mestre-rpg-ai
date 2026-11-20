"""Cliente HTTPX para consultar o Ollama local."""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class OllamaStatus:
    """Informacoes estruturadas sobre a disponibilidade do Ollama."""

    available: bool
    configured_model: str
    model_installed: bool
    version: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "version": self.version,
            "configured_model": self.configured_model,
            "model_installed": self.model_installed,
            "error": self.error,
        }


class OllamaClient:
    """Cliente para consulta das APIs publicas locais do Ollama."""

    def __init__(self, base_url: str, model: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def get_status(self) -> OllamaStatus:
        """Verifica versao e se o modelo configurado esta instalado."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                version_response = await client.get(f"{self.base_url}/api/version")
                version_response.raise_for_status()
                version_data = version_response.json()
                version = version_data.get("version")
                if not isinstance(version, str) or not version:
                    raise ValueError("Resposta de versao invalida")
            except httpx.TimeoutException:
                return OllamaStatus(False, self.model, False, error="O Ollama nao respondeu dentro do tempo limite")
            except httpx.ConnectError:
                return OllamaStatus(False, self.model, False, error="O Ollama nao esta acessivel")
            except (httpx.HTTPError, ValueError):
                return OllamaStatus(False, self.model, False, error="Falha ao consultar a versao do Ollama")

            try:
                tags_response = await client.get(f"{self.base_url}/api/tags")
                tags_response.raise_for_status()
                tags_data = tags_response.json()
            except httpx.TimeoutException:
                return OllamaStatus(False, self.model, False, version=version, error="O Ollama nao respondeu dentro do tempo limite")
            except httpx.ConnectError:
                return OllamaStatus(False, self.model, False, version=version, error="O Ollama nao esta acessivel")
            except (httpx.HTTPError, ValueError):
                return OllamaStatus(False, self.model, False, version=version, error="Falha ao consultar os modelos do Ollama")

            if not isinstance(tags_data, dict) or not isinstance(tags_data.get("models"), list):
                return OllamaStatus(False, self.model, False, version=version, error="Resposta de modelos invalida")

            installed_models = {
                item.get("name")
                for item in tags_data["models"]
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            model_installed = self.model in installed_models
            return OllamaStatus(
                available=True,
                configured_model=self.model,
                model_installed=model_installed,
                version=version,
                error=None if model_installed else "Modelo configurado nao esta instalado",
            )
