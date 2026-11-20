"""Configuracao principal da API FastAPI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.core.ai_engine.ollama_client import OllamaClient
from app.core.database import DatabaseManager


def configure_logging(log_dir: Path) -> logging.Logger:
    """Configura o logger da aplicacao."""

    logger = logging.getLogger("mestre_rpg")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


settings = get_settings()
logger = configure_logging(settings.log_dir)
database = DatabaseManager(settings.sqlalchemy_database_url)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gerencia inicializacao e encerramento controlados."""

    logger.info("Servidor iniciando em http://%s:%s", settings.host, settings.port)
    if database.check_available():
        logger.info("Banco de dados SQLite disponivel")
    else:
        logger.warning("Banco de dados SQLite indisponivel")
    yield
    database.dispose()
    logger.info("Servidor encerrado")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

frontend_dir = Path(__file__).resolve().parent / "frontend"
templates = Jinja2Templates(directory=str(frontend_dir / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(frontend_dir / "static")),
    name="static",
)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Registra erros internos sem expor detalhes ao cliente."""

    logger.error("Erro interno no caminho %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Erro interno do servidor"},
    )


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "ollama_model": settings.ollama_model,
        },
    )


@app.get("/api/health")
def health() -> dict:
    database_available = database.check_available()
    return {
        "status": "ok" if database_available else "degraded",
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "ok" if database_available else "degraded",
    }


@app.get("/api/health/ollama")
async def ollama_health() -> dict:
    client = OllamaClient(
        base_url=settings.ollama_api_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )
    status = await client.get_status()
    if not status.available:
        logger.warning("Ollama indisponivel: %s", status.error)
    elif not status.model_installed:
        logger.warning("Modelo Ollama nao instalado: %s", settings.ollama_model)
    return {
        "status": "ok" if status.available and status.model_installed else "degraded",
        "ollama": status.to_dict(),
    }
