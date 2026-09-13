import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.errors import CampaignNotFoundError
from app.contexts.campaign.application.queries.get_campaign import GetCampaignHandler
from app.contexts.campaign.application.queries.list_campaigns import (
    ListCampaignsHandler,
)
from app.contexts.campaign.domain.lead import LeadState
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import seed_tenant, two_step_campaign
from tests.integration.campaign.scenarios import start_campaign


def _get(session: AsyncSession) -> GetCampaignHandler:
    return GetCampaignHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


async def test_list_counts_leads_by_state(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    started, _ = await start_campaign(
        session, tenant, ["a@example.com", "b@example.com"]
    )
    draft = two_step_campaign(tenant, name="draft")
    await CampaignRepository(session).add(draft)
    await LeadRepository(session).add_many(
        draft.add_leads(["c@example.com"], known_emails=[])
    )

    summaries = await ListCampaignsHandler(
        CampaignRepository(session), LeadRepository(session)
    ).execute()

    counts = {summary.campaign.id: summary.lead_counts for summary in summaries}
    assert counts[started.id] == {LeadState.SCHEDULED: 2}
    assert counts[draft.id] == {LeadState.PENDING: 1}


async def test_detail_shows_the_next_send_time_per_lead(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    moment = now() + timedelta(minutes=1)
    started, (scheduled,) = await start_campaign(
        session, tenant, ["a@example.com"], moment=moment
    )
    late = started.add_leads(["late@example.com"], known_emails=["a@example.com"])
    await LeadRepository(session).add_many(late)

    detail = await _get(session).execute(started.id)

    next_send = {view.lead.email: view.next_send_at for view in detail.leads}
    assert next_send == {"a@example.com": moment, "late@example.com": None}
    assert detail.leads[0].lead.id == scheduled.id


async def test_detail_of_an_unknown_campaign_is_reported(
    session: AsyncSession,
) -> None:
    with pytest.raises(CampaignNotFoundError):
        await _get(session).execute(uuid.uuid7())
