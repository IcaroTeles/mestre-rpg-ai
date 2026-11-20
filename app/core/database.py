"""Conexao e sessoes independentes do banco SQLite."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class DatabaseManager:
    """Gerencia o engine e as sessoes SQLAlchemy."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

        if database_url.startswith("sqlite:"):
            self._ensure_sqlite_directory(database_url)

        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        engine_options: dict = {"connect_args": connect_args}
        if database_url in ("sqlite://", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:"):
            engine_options["poolclass"] = StaticPool

        self.engine: Engine = create_engine(database_url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @staticmethod
    def _ensure_sqlite_directory(database_url: str) -> None:
        if database_url in ("sqlite://", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:"):
            return

        prefix = "sqlite:///"
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix):]
            if raw_path.startswith("/") and len(raw_path) >= 3 and raw_path[2] == ":":
                raw_path = raw_path[1:]
            if raw_path and not raw_path.startswith(":"):
                Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def get_session(self) -> Session:
        """Abre uma nova sessao independente."""

        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Fornece uma sessao com encerramento garantido."""

        session = self.get_session()
        try:
            yield session
        finally:
            session.close()

    def check_available(self) -> bool:
        """Executa uma consulta leve sem modificar o banco."""

        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def dispose(self) -> None:
        """Libera conexoes mantidas pelo engine."""

        self.engine.dispose()
