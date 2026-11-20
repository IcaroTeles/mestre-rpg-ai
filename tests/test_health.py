"""Testes das rotas de estado da aplicacao."""

from fastapi.testclient import TestClient

from app.main import app


def test_app_import_and_startup() -> None:
    with TestClient(app) as client:
        assert client.app.title == "Mestre RPG AI"


def test_index_page() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Mestre RPG AI" in response.text
    assert "Verificando..." in response.text


def test_api_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["application"] == "Mestre RPG AI"
