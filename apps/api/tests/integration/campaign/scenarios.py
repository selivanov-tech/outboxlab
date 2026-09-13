from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.lead import Lead
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import Tenant, two_step_campaign


async def start_campaign(
    session: AsyncSession,
    tenant: Tenant,
    emails: list[str],
    *,
    campaign: Campaign | None = None,
    moment: datetime | None = None,
) -> tuple[Campaign, list[Lead]]:
    campaign = campaign or two_step_campaign(tenant)
    await CampaignRepository(session).add(campaign)
    leads = campaign.add_leads(emails, known_emails=[])
    await LeadRepository(session).add_many(leads)
    started, scheduled, jobs = campaign.start(leads, moment or now())
    await CampaignRepository(session).update_status(started)
    await LeadRepository(session).update_many(scheduled)
    await SendJobRepository(session).add_many(jobs)
    return started, scheduled
