"""Ponto de entrada da aplicacao Mestre RPG AI."""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Iniciando {settings.app_name} v{settings.app_version}")
    print(f"Servidor: http://{settings.host}:{settings.port}")
    print("Pressione Ctrl+C para encerrar.")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
