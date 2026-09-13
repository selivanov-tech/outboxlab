import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.commands.add_leads import AddLeadsHandler
from app.contexts.campaign.application.commands.create_campaign import (
    CreateCampaignCommand,
    CreateCampaignHandler,
)
from app.contexts.campaign.application.commands.start_campaign import (
    StartCampaignHandler,
)
from app.contexts.campaign.application.errors import (
    CampaignNotFoundError,
    MailboxNotConnectedError,
)
from app.contexts.campaign.domain.campaign import CampaignStatus, StepDraft
from app.contexts.campaign.domain.lead import LeadState
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.mailbox.lookup import MailboxLookup
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import Tenant, seed_tenant

COMMAND = CreateCampaignCommand(
    name="Q3 outreach",
    steps=(
        StepDraft(subject="Hello", body="First", delay_seconds=0),
        StepDraft(subject="Re: Hello", body="Second", delay_seconds=120),
    ),
)


def _create(session: AsyncSession) -> CreateCampaignHandler:
    return CreateCampaignHandler(
        MailboxLookup(MailboxRepository(session)), CampaignRepository(session)
    )


def _add_leads(session: AsyncSession) -> AddLeadsHandler:
    return AddLeadsHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


def _start(session: AsyncSession) -> StartCampaignHandler:
    return StartCampaignHandler(
        CampaignRepository(session), LeadRepository(session), SendJobRepository(session)
    )


async def _job_count(session: AsyncSession, tenant: Tenant) -> int:
    stmt = select(SendJobRow.id).where(SendJobRow.workspace_id == tenant.workspace_id)
    return len((await session.execute(stmt)).all())


async def test_create_uses_the_workspace_mailbox(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)

    campaign = await _create(session).execute(COMMAND, tenant.workspace_id)

    assert campaign.mailbox_id == tenant.mailbox_id
    assert await CampaignRepository(session).get(campaign.id) == campaign


async def test_create_without_a_mailbox_is_rejected(session: AsyncSession) -> None:
    workspace = Workspace.new("no-mailbox")
    await WorkspaceRepository(session).add(workspace)

    with pytest.raises(MailboxNotConnectedError):
        await _create(session).execute(COMMAND, workspace.id)


async def test_leads_wait_in_a_draft_and_are_scheduled_on_start(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    campaign = await _create(session).execute(COMMAND, tenant.workspace_id)

    added = await _add_leads(session).execute(
        campaign.id, ["a@example.com", "A@example.com", "b@example.com"], now()
    )

    assert (added.added, added.skipped, added.scheduled) == (2, 1, 0)
    assert await _job_count(session, tenant) == 0

    started = await _start(session).execute(campaign.id, now())

    assert started.campaign.status is CampaignStatus.ACTIVE
    assert started.scheduled == 2
    assert await _job_count(session, tenant) == 2
    leads = await LeadRepository(session).list_by_campaign(campaign.id)
    assert {lead.state for lead in leads} == {LeadState.SCHEDULED}


async def test_start_twice_schedules_nothing_new(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    campaign = await _create(session).execute(COMMAND, tenant.workspace_id)
    await _add_leads(session).execute(campaign.id, ["a@example.com"], now())
    await _start(session).execute(campaign.id, now())

    again = await _start(session).execute(campaign.id, now() + timedelta(seconds=5))

    assert again.scheduled == 0
    assert again.campaign.status is CampaignStatus.ACTIVE
    assert await _job_count(session, tenant) == 1


async def test_leads_added_to_an_active_campaign_are_scheduled_at_once(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    campaign = await _create(session).execute(COMMAND, tenant.workspace_id)
    await _start(session).execute(campaign.id, now())

    added = await _add_leads(session).execute(campaign.id, ["late@example.com"], now())

    assert (added.added, added.scheduled) == (1, 1)
    assert await _job_count(session, tenant) == 1


async def test_unknown_campaign_is_reported(session: AsyncSession) -> None:
    with pytest.raises(CampaignNotFoundError):
        await _start(session).execute(uuid.uuid7(), now())
    with pytest.raises(CampaignNotFoundError):
        await _add_leads(session).execute(uuid.uuid7(), ["a@example.com"], now())
