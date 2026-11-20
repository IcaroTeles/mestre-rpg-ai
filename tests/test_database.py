"""Testes da infraestrutura SQLite e gerenciamento de sessoes."""

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
