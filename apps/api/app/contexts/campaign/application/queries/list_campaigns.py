from dataclasses import dataclass

from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.lead import LeadState


@dataclass(frozen=True)
class CampaignSummary:
    campaign: Campaign
    lead_counts: dict[LeadState, int]


class ListCampaignsHandler:
    def __init__(
        self, campaigns: CampaignRepositoryPort, leads: LeadRepositoryPort
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads

    async def execute(self) -> list[CampaignSummary]:
        campaigns = await self._campaigns.list()
        counts = await self._leads.count_by_state([c.id for c in campaigns])
        return [
            CampaignSummary(campaign=campaign, lead_counts=counts.get(campaign.id, {}))
            for campaign in campaigns
        ]
