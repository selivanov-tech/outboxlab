import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.errors import CampaignNotFoundError
from app.contexts.campaign.application.queries.get_campaign_metrics import (
    GetCampaignMetricsHandler,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.shared.util.clock import now
from tests.integration.campaign.factories import seed_tenant
from tests.integration.campaign.scenarios import start_campaign
from tests.integration.campaign.test_process_send_jobs import (
    FakeGmailSender,
    process_due,
)


def _handler(session: AsyncSession) -> GetCampaignMetricsHandler:
    return GetCampaignMetricsHandler(
        CampaignRepository(session), LeadRepository(session)
    )


async def test_metrics_count_sends_replies_and_bounces(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    campaign, scheduled = await start_campaign(
        session,
        tenant,
        ["replied@example.com", "bounced@example.com", "waiting@example.com"],
    )
    await process_due(session, tenant, FakeGmailSender(), now() + timedelta(seconds=1))
    leads = {
        lead.email: lead
        for lead in await LeadRepository(session).list_by_campaign(campaign.id)
    }
    await LeadRepository(session).update_many(
        [
            campaign.stop_on_reply(leads["replied@example.com"], "positive", now()),
            campaign.stop_on_reply(leads["bounced@example.com"], "bounce", now()),
        ]
    )

    metrics = await _handler(session).execute(campaign.id)

    assert len(scheduled) == 3
    assert (metrics.leads, metrics.contacted, metrics.emails_sent) == (3, 3, 3)
    assert (metrics.replied, metrics.bounced) == (1, 1)
    assert metrics.reply_intents == {"positive": 1}
    assert (metrics.in_progress, metrics.completed) == (1, 0)
    assert metrics.reply_rate == pytest.approx(0.3333)
    assert metrics.bounce_rate == pytest.approx(0.3333)


async def test_metrics_of_a_campaign_without_sends_have_zero_rates(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    campaign, _ = await start_campaign(session, tenant, ["lead@example.com"])

    metrics = await _handler(session).execute(campaign.id)

    assert (metrics.leads, metrics.contacted, metrics.in_progress) == (1, 0, 1)
    assert (metrics.reply_rate, metrics.bounce_rate) == (0.0, 0.0)


async def test_metrics_of_an_unknown_campaign_are_reported(
    session: AsyncSession,
) -> None:
    with pytest.raises(CampaignNotFoundError):
        await _handler(session).execute(uuid.uuid7())
