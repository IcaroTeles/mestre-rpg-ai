"""Consultas e persistencia SQLAlchemy para campanhas."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database_models import Campaign, CampaignAuditEvent


class CampaignRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, campaign: Campaign) -> Campaign:
        self.session.add(campaign)
        return campaign

    def get_by_id(self, campaign_id: UUID) -> Campaign | None:
        return self.session.scalar(
            select(Campaign).where(Campaign.id == campaign_id)
        )

    def list_by_owner(self, owner_user_id: UUID) -> list[Campaign]:
        statement = (
            select(Campaign)
            .where(Campaign.owner_user_id == owner_user_id)
            .order_by(Campaign.created_at.desc(), Campaign.id)
        )
        return list(self.session.scalars(statement))

    def count_all(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Campaign)) or 0)

    def add_audit_event(self, event: CampaignAuditEvent) -> CampaignAuditEvent:
        self.session.add(event)
        return event

    def list_audit_events(self, campaign_id: UUID) -> list[CampaignAuditEvent]:
        statement = (
            select(CampaignAuditEvent)
            .where(CampaignAuditEvent.campaign_id == campaign_id)
            .order_by(CampaignAuditEvent.created_at, CampaignAuditEvent.id)
        )
        return list(self.session.scalars(statement))
