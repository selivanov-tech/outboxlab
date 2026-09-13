from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.contexts.campaign.application.process_send_jobs import SendJobOutcome
from app.contexts.campaign.domain.lead import LeadState, StopReason
from app.contexts.campaign.domain.send_job import SendJobStatus
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.domain.suppression import Suppression, SuppressionReason
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)
from app.shared.util.clock import now, start_of_utc_day
from tests.integration.campaign.factories import Tenant, seed_tenant
from tests.integration.campaign.scenarios import start_campaign
from tests.integration.campaign.test_process_send_jobs import (
    FakeGmailSender,
    process_due,
)


async def _job(session: AsyncSession, tenant: Tenant) -> SendJobRow:
    stmt = (
        select(SendJobRow)
        .where(SendJobRow.workspace_id == tenant.workspace_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalars().one()


async def test_suppressed_recipient_fails_the_lead_without_sending(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    _, (lead,) = await start_campaign(session, tenant, ["lead@example.com"])
    await SuppressionRepository(session).add(
        Suppression.new(
            workspace_id=tenant.workspace_id,
            email="lead@example.com",
            reason=SuppressionReason.HARD_BOUNCE,
            source_inbound_id=None,
        )
    )
    sender = FakeGmailSender()

    outcomes = await process_due(session, tenant, sender, now() + timedelta(seconds=1))

    assert outcomes == [SendJobOutcome.SUPPRESSED]
    assert sender.sent == []
    stored = await LeadRepository(session).get(lead.id)
    assert stored is not None
    assert (stored.state, stored.stop_reason) == (
        LeadState.FAILED,
        StopReason.SUPPRESSED,
    )
    assert (await _job(session, tenant)).status == SendJobStatus.CANCELLED.value


async def test_daily_cap_defers_the_job_to_the_next_utc_day(
    session: AsyncSession,
) -> None:
    workspace = Workspace.new("capped")
    await WorkspaceRepository(session).add(workspace)
    mailbox = Mailbox.new(workspace.id, "ops@example.com", daily_send_cap=0)
    await MailboxRepository(session).add(mailbox)
    tenant = Tenant(workspace_id=workspace.id, mailbox_id=mailbox.id)
    await start_campaign(session, tenant, ["lead@example.com"])
    sender = FakeGmailSender()
    moment = now() + timedelta(seconds=1)

    outcomes = await process_due(session, tenant, sender, moment)

    assert outcomes == [SendJobOutcome.DEFERRED]
    assert sender.sent == []
    job = await _job(session, tenant)
    assert job.status == SendJobStatus.PENDING.value
    assert job.attempts == 0
    assert job.scheduled_at == start_of_utc_day(moment) + timedelta(days=1)


async def test_busy_mailbox_defers_the_job_for_a_few_seconds(
    session: AsyncSession, engine: AsyncEngine
) -> None:
    tenant = await seed_tenant(session)
    await start_campaign(session, tenant, ["lead@example.com"])
    sender = FakeGmailSender()
    moment = now() + timedelta(seconds=1)
    lock_key = {"key": str(tenant.mailbox_id)}

    async with engine.connect() as other_sender:
        await other_sender.execute(
            text("SELECT pg_advisory_lock(hashtext(:key))"), lock_key
        )
        try:
            outcomes = await process_due(session, tenant, sender, moment)
        finally:
            await other_sender.execute(
                text("SELECT pg_advisory_unlock(hashtext(:key))"), lock_key
            )

    assert outcomes == [SendJobOutcome.DEFERRED]
    assert sender.sent == []
    job = await _job(session, tenant)
    assert job.status == SendJobStatus.PENDING.value
    assert job.attempts == 0
    assert timedelta(0) < job.scheduled_at - moment <= timedelta(seconds=30)
