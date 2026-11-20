"""Testes da camada interna de usuarios."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import DatabaseManager
from app.core.database_models import User
from app.core.user_engine.user_schemas import UserCreate, UserUpdate
from app.core.user_engine.user_service import (
    UserConflictError,
    UserNotFoundError,
    UserService,
)


@pytest.fixture
def database(tmp_path):
    database_path = tmp_path / "users.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    manager = DatabaseManager(f"sqlite:///{database_path.as_posix()}")
    yield manager
    manager.dispose()


@pytest.fixture
def service(database):
    return UserService(database)


def test_create_valid_user_generates_uuid_and_normalizes(service):
    user = service.create(
        UserCreate(
            username="  Mestre_01  ",
            email="  Mestre@Example.COM  ",
            display_name="  Mestre Icaro  ",
        )
    )

    assert isinstance(user.id, type(uuid4()))
    assert user.username == "mestre_01"
    assert user.email == "mestre@example.com"
    assert user.display_name == "Mestre Icaro"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.parametrize("username", ["ab", "nome com espaco", "nome@invalido", "", "a" * 31])
def test_reject_invalid_username(username):
    with pytest.raises(ValidationError):
        UserCreate(username=username, email="user@example.com", display_name="Usuario")


@pytest.mark.parametrize("email", ["", "sem-arroba", "@example.com", "user@", "user@dominio"])
def test_reject_invalid_email(email):
    with pytest.raises(ValidationError):
        UserCreate(username="usuario", email=email, display_name="Usuario")


@pytest.mark.parametrize("display_name", ["", "   ", "x" * 81])
def test_reject_invalid_display_name(display_name):
    with pytest.raises(ValidationError):
        UserCreate(username="usuario", email="user@example.com", display_name=display_name)


def test_duplicate_username_is_rejected(service):
    service.create(UserCreate(username="Jogador", email="one@example.com", display_name="Um"))

    with pytest.raises(UserConflictError):
        service.create(UserCreate(username="jOGADOR", email="two@example.com", display_name="Dois"))


def test_duplicate_email_is_rejected(service):
    service.create(UserCreate(username="JogadorUm", email="User@Example.com", display_name="Um"))

    with pytest.raises(UserConflictError):
        service.create(UserCreate(username="JogadorDois", email="  user@example.COM ", display_name="Dois"))


def test_find_by_id_username_and_email(service):
    created = service.create(
        UserCreate(username="JogadorUm", email="User@Example.com", display_name="Um")
    )

    assert service.get_by_id(created.id).id == created.id
    assert service.get_by_username(" JOGADORUM ").id == created.id
    assert service.get_by_email("user@example.COM").id == created.id


def test_list_with_pagination(service):
    for number in range(5):
        service.create(
            UserCreate(
                username=f"jogador{number}",
                email=f"jogador{number}@example.com",
                display_name=f"Jogador {number}",
            )
        )

    first_page = service.list(page=1, page_size=2)
    second_page = service.list(page=2, page_size=2)

    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {user.id for user in first_page}.isdisjoint({user.id for user in second_page})


def test_valid_update(service):
    created = service.create(
        UserCreate(username="jogador1", email="one@example.com", display_name="Um")
    )

    updated = service.update(
        created.id,
        UserUpdate(username="jogador_novo", display_name="Nome Novo"),
    )

    assert updated.username == "jogador_novo"
    assert updated.email == "one@example.com"
    assert updated.display_name == "Nome Novo"


def test_update_uniqueness_conflict(service):
    first = service.create(
        UserCreate(username="jogador1", email="one@example.com", display_name="Um")
    )
    service.create(
        UserCreate(username="jogador2", email="two@example.com", display_name="Dois")
    )

    with pytest.raises(UserConflictError):
        service.update(first.id, UserUpdate(username="JOGADOR2"))


def test_deactivate_and_reactivate(service):
    created = service.create(
        UserCreate(username="jogador1", email="one@example.com", display_name="Um")
    )

    deactivated = service.deactivate(created.id)
    assert deactivated.is_active is False

    reactivated = service.reactivate(created.id)
    assert reactivated.is_active is True


def test_user_not_found(service):
    missing = uuid4()

    with pytest.raises(UserNotFoundError):
        service.get_by_id(missing)
    with pytest.raises(UserNotFoundError):
        service.get_by_username("ausente")
    with pytest.raises(UserNotFoundError):
        service.deactivate(missing)


def test_persistence_after_engine_dispose(service, database):
    created = service.create(
        UserCreate(username="persistente", email="persistente@example.com", display_name="Persistente")
    )
    database.dispose()

    assert service.get_by_id(created.id).username == "persistente"


def test_database_rejects_duplicate_username(database):
    with database.transaction_scope() as session:
        session.add(
            User(
                username="duplicado",
                email="one@example.com",
                display_name="Um",
                is_active=True,
            )
        )

    with pytest.raises(IntegrityError):
        with database.transaction_scope() as session:
            session.add(
                User(
                    username="duplicado",
                    email="two@example.com",
                    display_name="Dois",
                    is_active=True,
                )
            )


def test_database_rejects_case_insensitive_duplicate_username(database):
    with database.transaction_scope() as session:
        session.execute(
            text(
                "INSERT INTO users "
                "(id, username, email, display_name, is_active, created_at, updated_at) "
                "VALUES (:id, 'Jogador', 'one@example.com', 'Um', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": str(uuid4())},
        )

    with pytest.raises(IntegrityError):
        with database.transaction_scope() as session:
            session.execute(
                text(
                    "INSERT INTO users "
                    "(id, username, email, display_name, is_active, created_at, updated_at) "
                    "VALUES (:id, 'jogador', 'two@example.com', 'Dois', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": str(uuid4())},
            )


def test_database_rejects_case_insensitive_duplicate_email(database):
    with database.transaction_scope() as session:
        session.execute(
            text(
                "INSERT INTO users "
                "(id, username, email, display_name, is_active, created_at, updated_at) "
                "VALUES (:id, 'one', 'Mestre@exemplo.com', 'Um', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": str(uuid4())},
        )

    with pytest.raises(IntegrityError):
        with database.transaction_scope() as session:
            session.execute(
                text(
                    "INSERT INTO users "
                    "(id, username, email, display_name, is_active, created_at, updated_at) "
                    "VALUES (:id, 'two', 'mestre@exemplo.com', 'Dois', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": str(uuid4())},
            )


def test_database_has_functional_unique_indexes(database):
    with database.engine.connect() as connection:
        indexes = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type='index' AND name LIKE 'uq_users_%'"
                )
            )
        }

    assert "LOWER(USERNAME)" in indexes["uq_users_username_normalized"].upper()
    assert "LOWER(EMAIL)" in indexes["uq_users_email_normalized"].upper()


def test_user_migration_upgrade_and_downgrade(tmp_path):
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    import sqlite3

    connection = sqlite3.connect(database_path)
    table_names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    connection.close()
    assert "users" in table_names

    command.downgrade(config, "base")

    connection = sqlite3.connect(database_path)
    table_names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    connection.close()
    assert "users" not in table_names
