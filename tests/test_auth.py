"""Testes de autenticacao, sessoes e cookies."""

import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.auth_engine.auth_service import (
    AuthService,
    InvalidCredentialsError,
    PasswordValidationError,
    SessionExpiredError,
    SessionRevokedError,
)
from app.core.database import DatabaseManager
from app.core.database_models import User
from app.core.user_engine.user_schemas import UserCreate
from app.core.user_engine.user_service import UserService
from app.main import app


@pytest.fixture
def database(tmp_path):
    database_path = tmp_path / "auth.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    manager = DatabaseManager(f"sqlite:///{database_path.as_posix()}")
    yield manager
    manager.dispose()


@pytest.fixture
def auth(database):
    return AuthService(database, session_duration_hours=12)


@pytest.fixture
def user(database):
    service = UserService(database)
    return service.create(
        UserCreate(
            username="MestreTeste",
            email="Mestre@Teste.com",
            display_name="Mestre Teste",
        )
    )


def test_set_password_valid_and_hash_is_not_plaintext(auth, user):
    auth.set_password(user.id, "SenhaSegura123")

    with auth.database.session_scope() as session:
        password_hash = session.get(User, user.id).password_hash

    assert password_hash
    assert "SenhaSegura123" not in password_hash
    assert password_hash.startswith("$argon2")
    assert auth.verify_password(password_hash, "SenhaSegura123") is True
    assert auth.verify_password(password_hash, "SenhaErrada123") is False


@pytest.mark.parametrize("password", ["", "            ", "curta", "a" * 129])
def test_password_policy_rejects_invalid_values(auth, user, password):
    with pytest.raises(PasswordValidationError):
        auth.set_password(user.id, password)


def test_password_change_revokes_sessions(auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    token, _, _, _ = auth.create_session(user.id)
    assert auth.get_session(token)

    auth.set_password(user.id, "OutraSenhaSegura123")

    with pytest.raises(SessionRevokedError):
        auth.get_session(token)


def test_login_username_and_email(auth, user):
    auth.set_password(user.id, "SenhaSegura123")

    assert auth.authenticate("mestreteste", "SenhaSegura123").id == user.id
    assert auth.authenticate("Mestre@Teste.com", "SenhaSegura123").id == user.id


def test_login_failures_are_generic(auth, user):
    with pytest.raises(InvalidCredentialsError):
        auth.authenticate("inexistente", "SenhaSegura123")

    auth.set_password(user.id, "SenhaSegura123")
    with pytest.raises(InvalidCredentialsError):
        auth.authenticate("mestreteste", "SenhaIncorreta")


def test_missing_account_uses_dummy_argon2_verification(auth):
    assert auth.dummy_password_hash.startswith("$argon2")
    with pytest.raises(InvalidCredentialsError):
        auth.authenticate("conta-inexistente", "SenhaSegura123")


def test_login_without_password(auth, user):
    with pytest.raises(InvalidCredentialsError):
        auth.authenticate("mestreteste", "SenhaSegura123")


def test_disabled_user_cannot_login(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    UserService(database).deactivate(user.id)

    with pytest.raises(InvalidCredentialsError):
        auth.authenticate("mestreteste", "SenhaSegura123")


def test_session_creation_validation_and_persistence(auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    token, csrf_token, expires_at, session_id = auth.create_session(user.id)

    assert len(token) >= 43
    assert csrf_token != token
    found_user, csrf_hash = auth.get_session(token)
    assert found_user.id == user.id
    assert csrf_hash == auth._hash_token(csrf_token)
    assert auth.validate_csrf(csrf_hash, csrf_token) is True
    assert expires_at > datetime.now(timezone.utc)
    assert session_id is not None


def test_invalid_revoked_and_expired_sessions(auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    token, _, _, _ = auth.create_session(user.id)
    auth.revoke_session(token)
    with pytest.raises(SessionRevokedError):
        auth.get_session(token)

    second_token, _, _, _ = auth.create_session(user.id)
    auth.revoke_all_user_sessions(user.id)
    with pytest.raises(SessionRevokedError):
        auth.get_session(second_token)

    with pytest.raises(Exception):
        auth.get_session("token-invalido")


def test_expired_session_is_rejected(auth, user, database):
    auth.set_password(user.id, "SenhaSegura123")
    token, _, _, _ = auth.create_session(user.id)
    token_hash = auth._hash_token(token)
    with database.transaction_scope() as session:
        from app.core.database_models import UserSession
        record = session.query(UserSession).filter_by(token_hash=token_hash).one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    with pytest.raises(SessionExpiredError):
        auth.get_session(token)


def test_session_persists_after_database_manager_recreation(auth, user, database, tmp_path):
    auth.set_password(user.id, "SenhaSegura123")
    token, _, _, _ = auth.create_session(user.id)

    database.dispose()
    recreated = DatabaseManager(database.database_url)
    recreated_auth = AuthService(recreated, 12)
    found_user, _ = recreated_auth.get_session(token)

    assert found_user.id == user.id
    recreated.dispose()


def test_disabled_user_revokes_session_and_reactivation_does_not_restore(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    token, _, _, _ = auth.create_session(user.id)

    UserService(database).deactivate(user.id)
    with pytest.raises(SessionRevokedError):
        auth.get_session(token)

    UserService(database).reactivate(user.id)
    with pytest.raises(SessionRevokedError):
        auth.get_session(token)


def test_login_http_sets_secure_cookie(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    app.state.database = database
    app.state.settings = type(
        "Settings",
        (),
        {"environment": "test"},
    )()

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
            headers={"Origin": "http://127.0.0.1:8000"},
        )

    assert response.status_code == 200
    assert "mestre_session" in response.cookies
    assert "mestre_csrf" in response.cookies
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Secure" not in set_cookie


def test_login_http_generic_failure(database, auth, user):
    app.state.database = database
    app.state.settings = type("Settings", (), {"environment": "test"})()
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username_or_email": "inexistente", "password": "SenhaSegura123"},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais invalidas"}


def test_login_http_rejects_missing_external_and_invalid_referer(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    app.state.database = database
    app.state.settings = type("Settings", (), {"environment": "test"})()

    with TestClient(app) as client:
        missing = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
        )
        external = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
            headers={"Origin": "https://externo.example"},
        )
        invalid_referer = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
            headers={"Referer": "https://externo.example/pagina"},
        )

    assert missing.status_code == 403
    assert external.status_code == 403
    assert invalid_referer.status_code == 403


def test_login_http_secure_cookie_in_production(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    app.state.database = database
    app.state.settings = type("Settings", (), {"environment": "production"})()

    with TestClient(app, base_url="https://mestre.local") as client:
        response = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
            headers={"Origin": "https://mestre.local"},
        )

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "Secure" in set_cookie


def test_me_logout_csrf_and_origin(database, auth, user):
    auth.set_password(user.id, "SenhaSegura123")
    app.state.database = database
    app.state.settings = type("Settings", (), {"environment": "test"})()

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"username_or_email": "mestreteste", "password": "SenhaSegura123"},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        csrf = login.json()["csrf_token"]

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "mestreteste"
        assert me.json()["csrf_token"] == csrf

        bad = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": "invalido", "Origin": "http://127.0.0.1:8000"},
        )
        assert bad.status_code == 403

        external = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": csrf, "Origin": "https://externo.example"},
        )
        assert external.status_code == 403

        missing_origin = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": csrf},
        )
        assert missing_origin.status_code == 403

        invalid_referer = client.post(
            "/api/auth/logout",
            headers={
                "X-CSRF-Token": csrf,
                "Referer": "https://externo.example/pagina",
            },
        )
        assert invalid_referer.status_code == 403

        logout = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:8000"},
        )
        assert logout.status_code == 200
        assert logout.json() == {"status": "logged_out"}

        after = client.get("/api/auth/me")
        assert after.status_code == 401


def test_migration_auth_upgrade_downgrade_reupgrade(tmp_path):
    database_path = tmp_path / "auth_migration.db"
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
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    connection.close()
    assert "users" in table_names
    assert "user_sessions" in table_names
    assert "password_hash" in columns

    command.downgrade(config, "8e1a4b2c53d7")

    connection = sqlite3.connect(database_path)
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    connection.close()
    assert "user_sessions" not in table_names
    assert "password_hash" not in columns

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
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    connection.close()
    assert "users" in table_names
    assert "user_sessions" in table_names
    assert "password_hash" in columns


def test_migration_auth_preserves_existing_user(tmp_path):
    database_path = tmp_path / "existing_auth.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "8e1a4b2c53d7")

    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT INTO users "
        "(id, username, email, display_name, is_active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (str(uuid4()), "existente", "existente@example.com", "Existente", 1),
    )
    connection.commit()
    connection.close()

    command.upgrade(config, "head")

    connection = sqlite3.connect(database_path)
    user_row = connection.execute(
        "SELECT username, password_hash FROM users WHERE username='existente'"
    ).fetchone()
    has_session_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_sessions'"
    ).fetchone()
    connection.close()

    assert user_row == ("existente", None)
    assert has_session_table == (1,)

    connection = sqlite3.connect(database_path)
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "users" in table_names
    assert "user_sessions" in table_names
    connection.close()

    command.downgrade(config, "8e1a4b2c53d7")

    connection = sqlite3.connect(database_path)
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    connection.close()
    assert "user_sessions" not in table_names
    assert "password_hash" not in columns

    command.upgrade(config, "head")
