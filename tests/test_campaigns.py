"""Testes da estrutura fundamental de campanhas."""

import sqlite3
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.auth_engine.auth_service import AuthService
from app.core.campaign_engine.campaign_schemas import CampaignCreate, CampaignUpdate
from app.core.campaign_engine.campaign_service import (
    CampaignForbiddenError,
    CampaignLimitReachedError,
    CampaignOwnerError,
    CampaignService,
    CampaignStateError,
    CampaignValidationError,
)
from app.core.campaign_engine.campaign_types import (
    CampaignDuration,
    CampaignFrequency,
    CampaignStatus,
)
from app.core.database import DatabaseManager
from app.core.database_models import Campaign, CampaignAuditEvent, User
from app.core.user_engine.user_schemas import UserCreate
from app.core.user_engine.user_service import UserService
from app.main import app


PREVIOUS_HEAD = "4a7c2e1d9f60"


@pytest.fixture
def database(tmp_path):
    database_path = tmp_path / "campaigns.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    manager = DatabaseManager(f"sqlite:///{database_path.as_posix()}")
    yield manager
    manager.dispose()


@pytest.fixture
def service(database):
    return CampaignService(database)


@pytest.fixture
def owner(database):
    return UserService(database).create(
        UserCreate(
            username="owner",
            email="owner@example.com",
            display_name="Owner",
        )
    )


def campaign_data(**overrides):
    data = {
        "name": "  A Jornada  ",
        "description": "  Uma campanha de teste  ",
        "duration_category": CampaignDuration.MEDIUM,
        "frequency": CampaignFrequency.WEEKLY,
    }
    data.update(overrides)
    return data


def test_create_campaign_sets_owner_state_defaults_and_audit(service, owner):
    campaign = service.create(owner.id, campaign_data())

    assert campaign.name == "A Jornada"
    assert campaign.description == "Uma campanha de teste"
    assert campaign.owner_user_id == owner.id
    assert campaign.status == CampaignStatus.PREPARATION
    assert campaign.planned_session_duration_minutes == 180
    assert campaign.created_at is not None
    assert campaign.updated_at is not None

    events = service.list_audit_events(owner.id, campaign.id)
    assert len(events) == 1
    assert events[0].action == "created"


def test_create_campaign_rejects_missing_or_inactive_owner(service, database):
    with pytest.raises(CampaignOwnerError):
        service.create(uuid4(), campaign_data())

    inactive = UserService(database).create(
        UserCreate(
            username="inativo",
            email="inativo@example.com",
            display_name="Inativo",
        )
    )
    UserService(database).deactivate(inactive.id)

    with pytest.raises(CampaignOwnerError):
        service.create(inactive.id, campaign_data())


def test_owner_can_start_pause_resume_end_and_explicitly_reopen(service, owner):
    campaign = service.create(owner.id, campaign_data())

    assert service.transition(owner.id, campaign.id, "start").status == CampaignStatus.ACTIVE
    assert service.transition(owner.id, campaign.id, "pause").status == CampaignStatus.PAUSED
    assert service.transition(owner.id, campaign.id, "resume").status == CampaignStatus.ACTIVE
    ended = service.transition(owner.id, campaign.id, "end")
    assert ended.status == CampaignStatus.ENDED
    assert service.get(owner.id, campaign.id).status == CampaignStatus.ENDED

    reopened = service.transition(owner.id, campaign.id, "reopen")
    assert reopened.status == CampaignStatus.PREPARATION
    events = service.list_audit_events(owner.id, campaign.id)
    assert [event.action for event in events][-1] == "reopened"


def test_invalid_campaign_transitions_are_rejected(service, owner):
    campaign = service.create(owner.id, campaign_data())

    with pytest.raises(CampaignStateError):
        service.transition(owner.id, campaign.id, "pause")
    service.transition(owner.id, campaign.id, "start")
    with pytest.raises(CampaignStateError):
        service.transition(owner.id, campaign.id, "start")
    service.transition(owner.id, campaign.id, "end")
    with pytest.raises(CampaignStateError):
        service.transition(owner.id, campaign.id, "pause")


def test_non_owner_cannot_read_update_or_end_campaign(
    service,
    owner,
    database,
):
    other = UserService(database).create(
        UserCreate(
            username="outro",
            email="outro@example.com",
            display_name="Outro",
        )
    )
    campaign = service.create(owner.id, campaign_data())

    with patch(
        "app.core.campaign_engine.campaign_service.logger.warning"
    ) as warning:
        with pytest.raises(CampaignForbiddenError):
            service.get(other.id, campaign.id)
        with pytest.raises(CampaignForbiddenError):
            service.update(other.id, campaign.id, {"name": "Tomada"})
        with pytest.raises(CampaignForbiddenError):
            service.transition(other.id, campaign.id, "end")
    assert warning.call_count == 3


def test_ended_campaign_remains_preserved_and_cannot_be_updated(service, owner):
    campaign = service.create(owner.id, campaign_data())
    service.transition(owner.id, campaign.id, "end")

    assert service.list_owned(owner.id)[0].id == campaign.id
    assert service.get(owner.id, campaign.id).status == CampaignStatus.ENDED
    with pytest.raises(CampaignStateError):
        service.update(owner.id, campaign.id, {"name": "Alterada"})


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("ONE_SHOT", CampaignDuration.ONE_SHOT),
        ("SHORT", CampaignDuration.SHORT),
        ("MEDIUM", CampaignDuration.MEDIUM),
        ("LONG", CampaignDuration.LONG),
    ],
)
def test_duration_categories_are_persisted(service, owner, category, expected):
    campaign = service.create(
        owner.id,
        campaign_data(duration_category=category),
    )
    assert campaign.duration_category == expected


def test_owner_can_change_duration_and_audit_captures_old_and_new(service, owner):
    campaign = service.create(owner.id, campaign_data())
    updated = service.update(
        owner.id,
        campaign.id,
        CampaignUpdate(duration_category=CampaignDuration.LONG),
    )

    assert updated.duration_category == CampaignDuration.LONG
    duration_events = [
        event
        for event in service.list_audit_events(owner.id, campaign.id)
        if event.action == "duration_category_changed"
    ]
    assert len(duration_events) == 1
    assert duration_events[0].details == {
        "field": "duration_category",
        "from": "MEDIUM",
        "to": "LONG",
    }


def test_date_and_session_duration_validation(service, owner):
    with pytest.raises(ValidationError):
        CampaignCreate.model_validate(campaign_data(name="   "))
    with pytest.raises(ValidationError):
        CampaignCreate.model_validate(
            campaign_data(
                start_date=date(2026, 12, 2),
                estimated_completion_date=date(2026, 12, 1),
            )
        )
    with pytest.raises(ValidationError):
        CampaignCreate.model_validate(
            campaign_data(planned_session_duration_minutes=119)
        )
    with pytest.raises(CampaignValidationError):
        service.update(
            owner.id,
            service.create(owner.id, campaign_data()).id,
            {
                "start_date": "2026-12-10",
                "estimated_completion_date": "2026-12-01",
            },
        )


def test_database_enforces_owner_foreign_key(database):
    with pytest.raises(IntegrityError):
        with database.transaction_scope() as session:
            session.add(
                Campaign(
                    id=uuid4(),
                    name="Sem owner",
                    owner_user_id=uuid4(),
                    status=CampaignStatus.PREPARATION,
                    duration_category=CampaignDuration.SHORT,
                    planned_session_duration_minutes=180,
                    frequency=CampaignFrequency.IRREGULAR,
                )
            )


def test_campaign_limit_is_global_and_optional(database, owner):
    limited = CampaignService(database, max_campaigns_total=1)
    limited.create(owner.id, campaign_data())

    second_owner = UserService(database).create(
        UserCreate(
            username="outroowner",
            email="outroowner@example.com",
            display_name="Outro Owner",
        )
    )
    with pytest.raises(CampaignLimitReachedError):
        limited.create(second_owner.id, campaign_data(name="Outra"))

    CampaignService(database).create(second_owner.id, campaign_data(name="Sem limite"))


def test_http_campaign_creation_requires_authentication_and_csrf(
    monkeypatch,
    database,
    owner,
):
    auth = AuthService(database)
    auth.set_password(owner.id, "SenhaSegura123")
    monkeypatch.setattr(app.state, "database", database)
    monkeypatch.setattr(
        app.state,
        "settings",
        SimpleNamespace(
            environment="test",
            campaign_max_total=None,
            get_trusted_origins=lambda: ("http://127.0.0.1:8000",),
        ),
    )

    with TestClient(app) as client:
        unauthenticated = client.post(
            "/api/campaigns",
            headers={"Origin": "http://127.0.0.1:8000"},
            json=campaign_data(),
        )
        assert unauthenticated.status_code == 401

        login = client.post(
            "/api/auth/login",
            headers={"Origin": "http://127.0.0.1:8000"},
            json={
                "username_or_email": "owner",
                "password": "SenhaSegura123",
            },
        )
        assert login.status_code == 200
        csrf = login.json()["csrf_token"]

        missing_csrf = client.post(
            "/api/campaigns",
            headers={"Origin": "http://127.0.0.1:8000"},
            json=campaign_data(),
        )
        assert missing_csrf.status_code == 403

        spoofed_owner = client.post(
            "/api/campaigns",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "X-CSRF-Token": csrf,
            },
            json={**campaign_data(), "owner_user_id": str(uuid4())},
        )
        assert spoofed_owner.status_code == 422

        created = client.post(
            "/api/campaigns",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "X-CSRF-Token": csrf,
            },
            json=campaign_data(),
        )
        assert created.status_code == 201
        assert created.json()["owner_user_id"] == str(owner.id)
        assert created.json()["status"] == "PREPARATION"


def test_campaign_api_has_no_delete_or_anonymous_write_routes():
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/api/campaigns" in paths
    assert "post" in paths["/api/campaigns"]
    assert not any(
        path.startswith("/api/campaigns")
        and "delete" in operations
        for path, operations in paths.items()
    )


def test_existing_invites_remain_compatible_with_campaign_migration(tmp_path):
    database_path = tmp_path / "campaign_migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, PREVIOUS_HEAD)

    user_id = str(uuid4())
    invite_id = str(uuid4())
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(
        "INSERT INTO users "
        "(id, username, email, display_name, is_active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (user_id, "legacy", "legacy@example.com", "Legacy"),
    )
    connection.execute(
        "INSERT INTO user_invites "
        "(id, token_hash, created_at, expires_at, created_by_user_id, purpose, campaign_id) "
        "VALUES (?, ?, CURRENT_TIMESTAMP, '2099-01-01 00:00:00', ?, 'player', NULL)",
        (invite_id, "a" * 64, user_id),
    )
    connection.commit()
    connection.close()

    command.upgrade(config, "head")
    connection = sqlite3.connect(database_path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    invite = connection.execute(
        "SELECT campaign_id FROM user_invites WHERE id=?",
        (invite_id,),
    ).fetchone()
    invite_foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(user_invites)"
    ).fetchall()
    connection.close()

    assert "campaigns" in tables
    assert "campaign_audit_events" in tables
    assert invite == (None,)
    assert all(row[3] != "campaign_id" for row in invite_foreign_keys)

    command.downgrade(config, PREVIOUS_HEAD)
    command.upgrade(config, "head")
    connection = sqlite3.connect(database_path)
    assert connection.execute(
        "SELECT campaign_id FROM user_invites WHERE id=?",
        (invite_id,),
    ).fetchone() == (None,)
    connection.close()


def test_campaign_and_audit_rows_are_committed_together(service, owner, database):
    campaign = service.create(owner.id, campaign_data())

    with database.session_scope() as session:
        campaign_row = session.get(Campaign, campaign.id)
        audit_rows = session.query(CampaignAuditEvent).filter_by(
            campaign_id=campaign.id
        ).all()
        audit_actor_user_id = audit_rows[0].actor_user_id

    assert campaign_row is not None
    assert len(audit_rows) == 1
    assert audit_actor_user_id == owner.id


def test_campaign_creation_rolls_back_if_audit_persistence_fails(
    monkeypatch,
    service,
    owner,
    database,
):
    def fail_audit(self, event):
        raise RuntimeError("falha simulada de auditoria")

    monkeypatch.setattr(
        "app.core.campaign_engine.campaign_service.CampaignRepository.add_audit_event",
        fail_audit,
    )

    with pytest.raises(RuntimeError, match="falha simulada de auditoria"):
        service.create(owner.id, campaign_data())

    with database.session_scope() as session:
        assert session.query(Campaign).count() == 0
        assert session.query(CampaignAuditEvent).count() == 0


def test_configuration_accepts_optional_global_campaign_limit():
    from app.config import Settings

    assert Settings(campaign_max_total=3).campaign_max_total == 3
    with pytest.raises(ValidationError):
        Settings(campaign_max_total=0)


def test_update_rejects_empty_payload():
    with pytest.raises(ValidationError):
        CampaignUpdate.model_validate({})

    with pytest.raises(ValidationError):
        CampaignUpdate.model_validate({"name": None})
