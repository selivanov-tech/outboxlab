from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.lead import LeadState, StopReason
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.shared.util.clock import now
from tests.integration.campaign.factories import seed_tenant, two_step_campaign


async def test_add_many_and_list_by_campaign(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    campaign = two_step_campaign(tenant)
    await CampaignRepository(session).add(campaign)
    repo = LeadRepository(session)
    leads = campaign.add_leads(["a@example.com", "b@example.com"], known_emails=[])

    await repo.add_many(leads)

    assert await repo.list_by_campaign(campaign.id) == leads
    assert await repo.emails(campaign.id) == {"a@example.com", "b@example.com"}
    assert await repo.get(leads[0].id) == leads[0]


async def test_list_pending_and_update_many(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    campaign = two_step_campaign(tenant)
    await CampaignRepository(session).add(campaign)
    repo = LeadRepository(session)
    first, second = campaign.add_leads(
        ["a@example.com", "b@example.com"], known_emails=[]
    )
    await repo.add_many([first, second])
    started, (scheduled,), _ = campaign.start([first], now())
    sent, _ = started.record_sent(scheduled, 1, now())
    paused = started.stop_on_reply(sent, "positive", now())

    await repo.update_many([paused])

    assert await repo.list_pending(campaign.id) == [second]
    stored = await repo.get(first.id)
    assert stored is not None
    assert stored.state is LeadState.PAUSED
    assert stored.steps_sent == 1
    assert stored.stop_reason is StopReason.REPLIED
    assert stored.reply_intent == "positive"
