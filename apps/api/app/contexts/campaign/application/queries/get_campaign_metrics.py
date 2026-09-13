from dataclasses import dataclass
from uuid import UUID

from app.contexts.campaign.application.errors import CampaignNotFoundError
from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.domain.campaign import BOUNCE_INTENT


@dataclass(frozen=True)
class CampaignMetrics:
    campaign_id: UUID
    leads: int
    contacted: int
    emails_sent: int
    replied: int
    reply_intents: dict[str, int]
    bounced: int
    in_progress: int
    completed: int
    reply_rate: float
    bounce_rate: float


class GetCampaignMetricsHandler:
    def __init__(
        self, campaigns: CampaignRepositoryPort, leads: LeadRepositoryPort
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads

    async def execute(self, campaign_id: UUID) -> CampaignMetrics:
        if await self._campaigns.get(campaign_id) is None:
            raise CampaignNotFoundError
        stats = await self._leads.stats(campaign_id)
        reply_intents = {
            intent: count
            for intent, count in stats.reply_intents.items()
            if intent != BOUNCE_INTENT
        }
        replied = sum(reply_intents.values())
        return CampaignMetrics(
            campaign_id=campaign_id,
            leads=stats.leads,
            contacted=stats.contacted,
            emails_sent=stats.emails_sent,
            replied=replied,
            reply_intents=reply_intents,
            bounced=stats.bounced,
            in_progress=stats.in_progress,
            completed=stats.completed,
            reply_rate=_share(replied, stats.contacted),
            bounce_rate=_share(stats.bounced, stats.contacted),
        )


def _share(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0
