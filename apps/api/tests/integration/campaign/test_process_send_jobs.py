from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.process_send_jobs import (
    ClaimDueSendJobsHandler,
    ProcessClaimedSendJobHandler,
    SendJobOutcome,
)
from app.contexts.campaign.domain.campaign import Campaign, StepDraft
from app.contexts.campaign.domain.lead import LeadState, StopReason
from app.contexts.campaign.domain.send_job import SendJobStatus
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.messaging.email_dispatch import (
    MessagingEmailDispatch,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.messaging.application.ports.email_sender import SentEmail
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import (
    STEP_TWO_DELAY_SECONDS,
    Tenant,
    seed_tenant,
)
from tests.integration.campaign.scenarios import start_campaign


class FakeGmailSender:
    def __init__(self, failures: int = 0) -> None:
        self.sent: list[tuple[str, str]] = []
        self._failures = failures

    async def send(
        self,
        *,
        mailbox_email: str,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> SentEmail:
        if self._failures:
            self._failures -= 1
            raise httpx.ConnectError("gmail down")
        self.sent.append((to_email, subject))
        number = len(self.sent)
        return SentEmail(
            provider_message_id=f"gmail-{number}",
            provider_thread_id=f"thread-{number}",
        )


async def process_due(
    session: AsyncSession,
    tenant: Tenant,
    sender: FakeGmailSender,
    moment: datetime,
) -> list[SendJobOutcome]:
    jobs = await ClaimDueSendJobsHandler(SendJobRepository(session)).execute(
        workspace_id=tenant.workspace_id,
        worker_id="worker-1",
        limit=10,
        moment=moment,
    )
    handler = ProcessClaimedSendJobHandler(
        CampaignRepository(session),
        LeadRepository(session),
        SendJobRepository(session),
        MessagingEmailDispatch(session, sender),
    )
    return [await handler.execute(job, moment) for job in jobs]


async def _jobs(session: AsyncSession, tenant: Tenant) -> list[SendJobRow]:
    stmt = (
        select(SendJobRow)
        .where(SendJobRow.workspace_id == tenant.workspace_id)
        .order_by(SendJobRow.created_at)
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(stmt)).scalars())


async def _outbound(session: AsyncSession, tenant: Tenant) -> list[OutboundMessageRow]:
    stmt = select(OutboundMessageRow).where(
        OutboundMessageRow.workspace_id == tenant.workspace_id
    )
    return list((await session.execute(stmt)).scalars())


async def test_first_step_is_sent_and_follow_up_is_scheduled(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    _, (lead,) = await start_campaign(session, tenant, ["lead@example.com"])
    sender = FakeGmailSender()

    outcomes = await process_due(session, tenant, sender, now() + timedelta(seconds=1))

    assert outcomes == [SendJobOutcome.SENT]
    assert sender.sent == [("lead@example.com", "Hello")]
    (outbound,) = await _outbound(session, tenant)
    stored = await LeadRepository(session).get(lead.id)
    assert stored is not None
    assert (stored.state, stored.steps_sent) == (LeadState.SENT, 1)
    first, follow_up = await _jobs(session, tenant)
    assert first.status == SendJobStatus.DONE.value
    assert first.outbound_message_id == outbound.id
    assert follow_up.status == SendJobStatus.PENDING.value
    assert follow_up.payload["step_position"] == 2
    assert follow_up.scheduled_at - outbound.created_at == timedelta(
        seconds=STEP_TWO_DELAY_SECONDS
    )


async def test_last_step_finishes_the_lead(session: AsyncSession) -> None:
    tenant = await seed_tenant(session)
    one_step = Campaign.new(
        workspace_id=tenant.workspace_id,
        mailbox_id=tenant.mailbox_id,
        name="single",
        steps=[StepDraft(subject="Only", body="Once", delay_seconds=0)],
    )
    _, (lead,) = await start_campaign(
        session, tenant, ["lead@example.com"], campaign=one_step
    )

    outcomes = await process_due(
        session, tenant, FakeGmailSender(), now() + timedelta(seconds=1)
    )

    assert outcomes == [SendJobOutcome.SENT]
    stored = await LeadRepository(session).get(lead.id)
    assert stored is not None
    assert stored.state is LeadState.DONE
    assert [job.status for job in await _jobs(session, tenant)] == [
        SendJobStatus.DONE.value
    ]


async def test_send_errors_are_retried_then_the_lead_fails(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    _, (lead,) = await start_campaign(session, tenant, ["lead@example.com"])
    sender = FakeGmailSender(failures=3)
    moment = now() + timedelta(seconds=1)

    assert await process_due(session, tenant, sender, moment) == [
        SendJobOutcome.RETRYING
    ]
    (job,) = await _jobs(session, tenant)
    assert job.status == SendJobStatus.PENDING.value
    assert job.scheduled_at == moment + timedelta(seconds=60)
    assert await _outbound(session, tenant) == []

    moment += timedelta(seconds=61)
    assert await process_due(session, tenant, sender, moment) == [
        SendJobOutcome.RETRYING
    ]
    moment += timedelta(seconds=121)
    assert await process_due(session, tenant, sender, moment) == [SendJobOutcome.FAILED]

    (job,) = await _jobs(session, tenant)
    assert job.status == SendJobStatus.FAILED.value
    assert job.last_error is not None and "gmail down" in job.last_error
    stored = await LeadRepository(session).get(lead.id)
    assert stored is not None
    assert (stored.state, stored.stop_reason) == (
        LeadState.FAILED,
        StopReason.SEND_FAILED,
    )
    assert sender.sent == []


async def test_follow_up_for_a_paused_lead_is_cancelled(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    campaign, (lead,) = await start_campaign(session, tenant, ["lead@example.com"])
    sender = FakeGmailSender()
    moment = now() + timedelta(seconds=1)
    await process_due(session, tenant, sender, moment)
    sent = await LeadRepository(session).get(lead.id)
    assert sent is not None
    await LeadRepository(session).update_many(
        [campaign.stop_on_reply(sent, "positive", moment)]
    )

    outcomes = await process_due(
        session,
        tenant,
        sender,
        moment + timedelta(seconds=STEP_TWO_DELAY_SECONDS + 5),
    )

    assert outcomes == [SendJobOutcome.CANCELLED]
    assert len(sender.sent) == 1
    assert [job.status for job in await _jobs(session, tenant)] == [
        SendJobStatus.DONE.value,
        SendJobStatus.CANCELLED.value,
    ]
