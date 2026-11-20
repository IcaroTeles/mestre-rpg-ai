"""Testes da Microetapa 2.4 de convites."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.auth_engine.auth_service import AuthService
from app.core.database import DatabaseManager
from app.core.database_models import User, UserInvite
from app.core.invite_engine.invite_schemas import AcceptInviteRequest
from app.core.invite_engine.invite_service import (
    InviteExpiredError,
    InviteRevokedError,
    InviteUnauthorizedError,
    InviteUsedError,
    InviteService,
)
from app.core.user_engine.user_schemas import UserCreate
from app.core.user_engine.user_service import UserService
from app.main import app


@pytest.fixture
def database(tmp_path):
    database_path = tmp_path / "invites.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    manager = DatabaseManager(f"sqlite:///{database_path.as_posix()}")
    yield manager
    manager.dispose()


@pytest.fixture
def creator(database):
    return UserService(database).create(
        UserCreate(
            username="administrador",
            email="admin@example.com",
            display_name="Administrador",
        )
    )


@pytest.fixture
def invite_service(database):
    return InviteService(database, validity_hours=48)


def test_create_invite_valid_default_and_hash(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )

    assert len(created.token) >= 43
    assert created.invite.created_by_user_id == creator.id
    assert created.invite.used_at is None
    assert created.invite.revoked_at is None
    assert created.invite.purpose == "player"
    assert created.invite.expires_at > created.invite.created_at
    assert created.invite.expires_at - created.invite.created_at >= timedelta(hours=47)

    with database.session_scope() as session:
        row = session.execute(
            text("SELECT token_hash FROM user_invites")
        ).one()
    assert row.token_hash != created.token
    assert len(row.token_hash) == 64


def test_create_invite_custom_validity(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
        validity_hours=12,
    )
    assert created.invite.expires_at - created.invite.created_at >= timedelta(hours=11)


def test_create_invite_requires_explicit_authorization(invite_service, creator):
    with pytest.raises(InviteUnauthorizedError):
        invite_service.create_invite(
            creator.id,
            authorized_as_administrator=False,
        )


def test_accept_invite_creates_password_user_and_session(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )

    user, session_token, csrf_token = invite_service.accept_invite(
        AcceptInviteRequest(
            token=created.token,
            username="JogadorNovo",
            email="Jogador@Exemplo.com",
            display_name="Jogador Novo",
            password="SenhaSegura123",
        )
    )

    assert user.username == "jogadornovo"
    assert user.email == "jogador@exemplo.com"
    assert session_token
    assert csrf_token

    with database.session_scope() as session:
        row = session.get(User, user.id)
        invite_row = session.get(UserInvite, created.invite.id)
        assert row is not None
        password_hash = row.password_hash
        is_active = row.is_active
        used_at = invite_row.used_at
        used_by_user_id = invite_row.used_by_user_id

    assert password_hash.startswith("$argon2")
    assert is_active is True
    assert used_at is not None
    assert used_by_user_id == user.id


def test_reuse_invite_is_rejected(invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )
    data = AcceptInviteRequest(
        token=created.token,
        username="JogadorUm",
        email="um@example.com",
        display_name="Jogador Um",
        password="SenhaSegura123",
    )
    invite_service.accept_invite(data)

    with pytest.raises(InviteUsedError):
        invite_service.accept_invite(
            AcceptInviteRequest(
                token=created.token,
                username="JogadorDois",
                email="dois@example.com",
                display_name="Jogador Dois",
                password="SenhaSegura123",
            )
        )


def test_expired_invite_is_rejected(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )
    with database.transaction_scope() as session:
        invite = session.get(UserInvite, created.invite.id)
        invite.expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).replace(tzinfo=None)

    with pytest.raises(InviteExpiredError):
        invite_service.accept_invite(
            AcceptInviteRequest(
                token=created.token,
                username="Expirado",
                email="expirado@example.com",
                display_name="Expirado",
                password="SenhaSegura123",
            )
        )


def test_revoked_invite_is_rejected(invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )
    invite_service.revoke_invite(created.invite.id)

    with pytest.raises(InviteRevokedError):
        invite_service.accept_invite(
            AcceptInviteRequest(
                token=created.token,
                username="Revogado",
                email="revogado@example.com",
                display_name="Revogado",
                password="SenhaSegura123",
            )
        )


def test_invalid_duplicate_and_failed_acceptance_do_not_consume(invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )

    with pytest.raises(Exception):
        invite_service.accept_invite(
            AcceptInviteRequest(
                token="a" * 43,
                username="Invalido",
                email="invalido@example.com",
                display_name="Invalido",
                password="SenhaSegura123",
            )
        )

    service = invite_service
    with pytest.raises(Exception):
        service.accept_invite(
            AcceptInviteRequest(
                token=created.token,
                username="administrador",
                email="novo@example.com",
                display_name="Duplicado",
                password="SenhaSegura123",
            )
        )

    user, _, _ = service.accept_invite(
        AcceptInviteRequest(
            token=created.token,
            username="Valido",
            email="valido@example.com",
            display_name="Valido",
            password="SenhaSegura123",
        )
    )
    assert user.username == "valido"


def test_concurrent_accept_only_creates_one_user(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )

    def accept(username, email):
        try:
            return invite_service.accept_invite(
                AcceptInviteRequest(
                    token=created.token,
                    username=username,
                    email=email,
                    display_name="Concorrente",
                    password="SenhaSegura123",
                )
            )
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(accept, "concorrente1", "one@example.com")
        second = executor.submit(accept, "concorrente2", "two@example.com")
        results = [first.result(), second.result()]

    successes = [result for result in results if not isinstance(result, Exception)]
    failures = [result for result in results if isinstance(result, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1


def test_accept_http_sets_session_cookie(database, invite_service, creator):
    created = invite_service.create_invite(
        creator.id,
        authorized_as_administrator=True,
    )
    app.state.database = database
    app.state.settings = type(
        "Settings",
        (),
        {
            "environment": "test",
            "invite_validity_hours": 48,
            "get_trusted_origins": staticmethod(
                lambda: (
                    "http://127.0.0.1:8000",
                    "http://localhost:8000",
                )
            ),
        },
    )()

    with TestClient(app) as client:
        response = client.post(
            "/api/invites/accept",
            headers={"Origin": "http://127.0.0.1:8000"},
            json={
                "token": created.token,
                "username": "ViaHttp",
                "email": "viahttp@example.com",
                "display_name": "Via HTTP",
                "password": "SenhaSegura123",
            },
        )

    assert response.status_code == 200
    assert "mestre_session" in response.cookies
    assert "mestre_csrf" in response.cookies
    assert "csrf_token" in response.json()


def test_migration_invites_upgrade_downgrade_reupgrade(tmp_path):
    database_path = tmp_path / "invites_migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    connection = sqlite3.connect(database_path)
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(user_invites)").fetchall()
    }
    connection.close()

    assert "user_invites" in table_names
    assert "users" in table_names
    assert "user_sessions" in table_names
    assert "token_hash" in columns
    assert "used_by_user_id" in columns

    command.downgrade(config, "9c41d7e2a8f5")

    connection = sqlite3.connect(database_path)
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    connection.close()
    assert "user_invites" not in table_names

    command.upgrade(config, "head")
