"""Testes da infraestrutura SQLite e gerenciamento de sessoes."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.database import DatabaseManager


def test_sqlite_memory_database_available() -> None:
    database = DatabaseManager("sqlite+pysqlite:///:memory:")

    assert database.check_available() is True
    database.dispose()


def test_database_session_is_closed_by_scope(tmp_path) -> None:
    database_path = tmp_path / "test.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.session_scope() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
        assert session.in_transaction() is True

    assert session.in_transaction() is False
    database.dispose()


def test_database_file_is_created(tmp_path) -> None:
    nested_directory = tmp_path / "nested"
    database_path = nested_directory / "mestre.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    assert database.check_available() is True
    assert database_path.exists()
    database.dispose()


def test_auto_directory_creation(tmp_path) -> None:
    nested_directory = tmp_path / "new" / "deeper"
    database_path = nested_directory / "mestre.db"

    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    assert nested_directory.exists()
    assert database.check_available() is True
    database.dispose()


def test_session_closes_and_rolls_back_after_exception(tmp_path) -> None:
    database_path = tmp_path / "rollback.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)"))

    try:
        with database.session_scope() as session:
            session.execute(text("INSERT INTO sample(value) VALUES ('draft')"))
            raise RuntimeError("falha simulada")
    except RuntimeError:
        pass

    with database.session_scope() as session:
        assert session.execute(text("SELECT COUNT(*) FROM sample")).scalar_one() == 0
    database.dispose()


def test_transaction_scope_commits_on_success(tmp_path) -> None:
    database_path = tmp_path / "commit.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)"))

    with database.transaction_scope() as session:
        session.execute(text("INSERT INTO sample(value) VALUES ('saved')"))

    with database.session_scope() as session:
        assert session.execute(text("SELECT value FROM sample")).scalar_one() == "saved"
    database.dispose()


def test_transaction_scope_rolls_back_on_failure(tmp_path) -> None:
    database_path = tmp_path / "failure.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)"))

    try:
        with database.transaction_scope() as session:
            session.execute(text("INSERT INTO sample(value) VALUES ('temporary')"))
            raise RuntimeError("falha transacional")
    except RuntimeError:
        pass

    with database.session_scope() as session:
        assert session.execute(text("SELECT COUNT(*) FROM sample")).scalar_one() == 0
    database.dispose()


def test_sessions_are_isolated_on_disk(tmp_path) -> None:
    database_path = tmp_path / "isolation.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)"))

    with database.transaction_scope() as first:
        first.execute(text("INSERT INTO sample(value) VALUES ('private')"))

        with database.session_scope() as second_before_commit:
            assert second_before_commit.execute(
                text("SELECT COUNT(*) FROM sample")
            ).scalar_one() == 0

    with database.session_scope() as second_after_commit:
        assert second_after_commit.execute(
            text("SELECT COUNT(*) FROM sample")
        ).scalar_one() == 1
    database.dispose()


def test_check_available_after_engine_dispose(tmp_path) -> None:
    database_path = tmp_path / "rediscover.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    assert database.check_available() is True
    database.dispose()
    assert database.check_available() is True


def test_check_available_handles_unavailable_database(tmp_path) -> None:
    blocked_path = tmp_path / "blocked"
    blocked_path.mkdir()
    database = DatabaseManager(f"sqlite:///{blocked_path.as_posix()}")

    assert database.check_available() is False
    database.dispose()


def test_foreign_keys_are_enabled(tmp_path) -> None:
    database_path = tmp_path / "foreign_keys.db"
    database = DatabaseManager(f"sqlite:///{database_path.as_posix()}")

    with database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
    database.dispose()


def test_memory_database_supports_check_thread_and_pragmas() -> None:
    database = DatabaseManager("sqlite+pysqlite:///:memory:")

    with database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
    assert database.check_available() is True
    database.dispose()


def test_alembic_works_with_temporary_database(tmp_path) -> None:
    database_path = tmp_path / "alembic.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    assert database_path.exists()
