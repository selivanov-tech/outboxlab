from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contexts.campaign.application.errors import CampaignNotFoundError
from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.application.ports.send_job_repository import (
    SendJobRepositoryPort,
)
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.lead import Lead


@dataclass(frozen=True)
class LeadView:
    lead: Lead
    next_send_at: datetime | None


@dataclass(frozen=True)
class CampaignDetail:
    campaign: Campaign
    leads: list[LeadView]


class GetCampaignHandler:
    def __init__(
        self,
        campaigns: CampaignRepositoryPort,
        leads: LeadRepositoryPort,
        jobs: SendJobRepositoryPort,
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads
        self._jobs = jobs

    async def execute(self, campaign_id: UUID) -> CampaignDetail:
        campaign = await self._campaigns.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError
        next_send_at = await self._jobs.next_send_at_by_lead(campaign_id)
        return CampaignDetail(
            campaign=campaign,
            leads=[
                LeadView(lead=lead, next_send_at=next_send_at.get(lead.id))
                for lead in await self._leads.list_by_campaign(campaign_id)
            ],
        )
