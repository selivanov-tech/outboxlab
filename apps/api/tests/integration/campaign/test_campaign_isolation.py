from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from tests.integration.campaign.factories import seed_tenant, two_step_campaign


async def _set_workspace(session: AsyncSession, workspace_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.workspace_id', :id, true)"),
        {"id": workspace_id},
    )


async def _visible(session: AsyncSession, sql: str) -> list[str]:
    return [str(value) for value in (await session.execute(text(sql))).scalars()]


async def test_steps_and_leads_are_isolated_per_workspace(
    session: AsyncSession,
) -> None:
    tenant_a = await seed_tenant(session, "tenant-a")
    tenant_b = await seed_tenant(session, "tenant-b")

    # Superuser bypasses RLS even with FORCE; the app role makes the policy apply.
    await session.execute(text("SET LOCAL ROLE outboxlab_app"))

    campaigns = {}
    for tenant, email in ((tenant_a, "a@example.com"), (tenant_b, "b@example.com")):
        await _set_workspace(session, str(tenant.workspace_id))
        campaign = two_step_campaign(tenant)
        await CampaignRepository(session).add(campaign)
        await LeadRepository(session).add_many(
            campaign.add_leads([email], known_emails=[])
        )
        campaigns[tenant] = campaign

    await _set_workspace(session, str(tenant_a.workspace_id))
    assert await _visible(session, "SELECT email FROM campaign__leads") == [
        "a@example.com"
    ]
    assert await _visible(
        session, "SELECT DISTINCT campaign_id FROM campaign__steps"
    ) == [str(campaigns[tenant_a].id)]

    await _set_workspace(session, str(tenant_b.workspace_id))
    assert await _visible(session, "SELECT email FROM campaign__leads") == [
        "b@example.com"
    ]
