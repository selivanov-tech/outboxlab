from collections.abc import Sequence
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


@dataclass(frozen=True)
class AddLeadsResult:
    added: int
    skipped: int
    scheduled: int


class AddLeadsHandler:
    def __init__(
        self,
        campaigns: CampaignRepositoryPort,
        leads: LeadRepositoryPort,
        jobs: SendJobRepositoryPort,
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads
        self._jobs = jobs

    async def execute(
        self, campaign_id: UUID, emails: Sequence[str], moment: datetime
    ) -> AddLeadsResult:
        campaign = await self._campaigns.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError
        new_leads = campaign.add_leads(emails, await self._leads.emails(campaign_id))
        await self._leads.add_many(new_leads)
        scheduled = 0
        if campaign.is_active and new_leads:
            scheduled_leads, jobs = campaign.schedule(new_leads, moment)
            await self._leads.update_many(scheduled_leads)
            await self._jobs.add_many(jobs)
            scheduled = len(scheduled_leads)
        return AddLeadsResult(
            added=len(new_leads),
            skipped=len(emails) - len(new_leads),
            scheduled=scheduled,
        )
