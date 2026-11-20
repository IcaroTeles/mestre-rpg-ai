"""Testes do cliente e da rota de estado do Ollama."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.ai_engine.ollama_client import OllamaClient
from app.main import app


@pytest.mark.asyncio
async def test_ollama_available_with_installed_model() -> None:
    version_response = httpx.Response(
        200,
        json={"version": "0.12.0"},
        request=httpx.Request("GET", "http://127.0.0.1:11434/api/version"),
    )
    tags_response = httpx.Response(
        200,
        json={"models": [{"name": "gemma3:12b"}, {"name": "other:model"}]},
        request=httpx.Request("GET", "http://127.0.0.1:11434/api/tags"),
    )

    mock_client = AsyncMock()
    mock_client.get.side_effect = [version_response, tags_response]
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.core.ai_engine.ollama_client.httpx.AsyncClient", return_value=mock_client):
        status = await OllamaClient("http://127.0.0.1:11434", "gemma3:12b").get_status()

    assert status.available is True
    assert status.model_installed is True
    assert status.version == "0.12.0"


@pytest.mark.asyncio
async def test_ollama_unavailable() -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("indisponivel")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.core.ai_engine.ollama_client.httpx.AsyncClient", return_value=mock_client):
        status = await OllamaClient("http://127.0.0.1:11434", "gemma3:12b").get_status()

    assert status.available is False
    assert status.model_installed is False
    assert status.error is not None


@pytest.mark.asyncio
async def test_model_configured_not_installed() -> None:
    version_response = httpx.Response(
        200,
        json={"version": "0.12.0"},
        request=httpx.Request("GET", "http://127.0.0.1:11434/api/version"),
    )
    tags_response = httpx.Response(
        200,
        json={"models": [{"name": "llama3.2:3b"}]},
        request=httpx.Request("GET", "http://127.0.0.1:11434/api/tags"),
    )

    mock_client = AsyncMock()
    mock_client.get.side_effect = [version_response, tags_response]
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.core.ai_engine.ollama_client.httpx.AsyncClient", return_value=mock_client):
        status = await OllamaClient("http://127.0.0.1:11434", "gemma3:12b").get_status()

    assert status.available is True
    assert status.model_installed is False
    assert status.error is not None


def test_ollama_health_route_without_service() -> None:
    from app.core.ai_engine.ollama_client import OllamaStatus

    status = OllamaStatus(
        available=False,
        configured_model="gemma3:12b",
        model_installed=False,
        error="O Ollama nao esta acessivel",
    )
    with patch("app.main.OllamaClient.get_status", new=AsyncMock(return_value=status)):
        with TestClient(app) as client:
            response = client.get("/api/health/ollama")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["ollama"]["available"] is False
