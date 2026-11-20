"""Conexao e sessoes independentes do banco SQLite."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class DatabaseManager:
    """Gerencia o engine e as sessoes SQLAlchemy."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        url = make_url(database_url)
        is_sqlite_memory = url.database in (None, "", ":memory:")

        if url.get_backend_name() == "sqlite" and not is_sqlite_memory:
            self._ensure_sqlite_directory(database_url)

        connect_args = {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
        engine_options: dict = {"connect_args": connect_args}
        if is_sqlite_memory and url.get_backend_name() == "sqlite":
            engine_options["poolclass"] = StaticPool

        self.engine: Engine = create_engine(database_url, **engine_options)
        if url.get_backend_name() == "sqlite":
            self._configure_sqlite_connection()
            if not is_sqlite_memory:
                try:
                    with self.engine.begin() as connection:
                        connection.execute(text("PRAGMA journal_mode=WAL"))
                except Exception:
                    pass
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @staticmethod
    def _ensure_sqlite_directory(database_url: str) -> None:
        database_path = make_url(database_url).database
        if database_path:
            Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def _configure_sqlite_connection(self) -> None:
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
            del connection_record
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    def get_session(self) -> Session:
        """Abre uma nova sessao independente."""

        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Fornece uma sessao somente leitura sem commits automaticos."""

        session = self.get_session()
        try:
            yield session
            session.rollback()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def transaction_scope(self) -> Iterator[Session]:
        """Executa uma transacao com commit explicito em caso de sucesso."""

        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
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
