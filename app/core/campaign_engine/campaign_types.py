"""Tipos compartilhados pela persistencia e validacao de campanhas."""

from enum import StrEnum


class CampaignStatus(StrEnum):
    PREPARATION = "PREPARATION"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDED = "ENDED"


class CampaignDuration(StrEnum):
    ONE_SHOT = "ONE_SHOT"
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"


class CampaignFrequency(StrEnum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    IRREGULAR = "IRREGULAR"
