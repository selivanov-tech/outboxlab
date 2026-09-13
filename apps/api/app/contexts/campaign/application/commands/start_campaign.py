from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contexts.campaign.application.errors import (
    CampaignHasNoLeadsError,
    CampaignNotFoundError,
)
from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.application.ports.send_job_repository import (
    SendJobRepositoryPort,
)
from app.contexts.campaign.domain.campaign import Campaign


@dataclass(frozen=True)
class StartCampaignResult:
    campaign: Campaign
    scheduled: int


class StartCampaignHandler:
    def __init__(
        self,
        campaigns: CampaignRepositoryPort,
        leads: LeadRepositoryPort,
        jobs: SendJobRepositoryPort,
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads
        self._jobs = jobs

    async def execute(self, campaign_id: UUID, moment: datetime) -> StartCampaignResult:
        campaign = await self._campaigns.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError
        if campaign.is_active:
            return StartCampaignResult(campaign=campaign, scheduled=0)
        pending = await self._leads.list_pending(campaign_id)
        if not pending:
            raise CampaignHasNoLeadsError
        started, scheduled, jobs = campaign.start(pending, moment)
        await self._campaigns.update_status(started)
        await self._leads.update_many(scheduled)
        await self._jobs.add_many(jobs)
        return StartCampaignResult(campaign=started, scheduled=len(scheduled))
