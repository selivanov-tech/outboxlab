from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.domain.campaign import CampaignStatus
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import seed_tenant, two_step_campaign


async def test_add_and_get_roundtrip_with_steps(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    repo = CampaignRepository(session)
    campaign = two_step_campaign(tenant)

    await repo.add(campaign)

    assert await repo.get(campaign.id) == campaign


async def test_list_returns_newest_first(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    repo = CampaignRepository(session)
    older = two_step_campaign(tenant, name="older")
    newer = two_step_campaign(tenant, name="newer")
    await repo.add(older)
    await repo.add(newer)

    listed = await repo.list()

    assert [campaign.name for campaign in listed[:2]] == ["newer", "older"]
    assert [step.position for step in listed[0].steps] == [1, 2]


async def test_update_status_persists(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    repo = CampaignRepository(session)
    campaign = two_step_campaign(tenant)
    await repo.add(campaign)
    started, _, _ = campaign.start([], now())

    await repo.update_status(started)

    fetched = await repo.get(campaign.id)
    assert fetched is not None
    assert fetched.status is CampaignStatus.ACTIVE
