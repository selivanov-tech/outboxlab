from datetime import timedelta

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
from app.contexts.campaign.application.handle_classified_replies import (
    HandleClassifiedRepliesHandler,
)
from app.contexts.campaign.domain.campaign import StepDraft
from app.contexts.campaign.domain.lead import LeadState, StopReason
from app.contexts.campaign.domain.send_job import SendJobStatus
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow
from app.contexts.campaign.infrastructure.mailbox.lookup import MailboxLookup
from app.contexts.campaign.infrastructure.messaging.reply_feed import (
    ClassifiedReplyFeed,
)
from app.contexts.campaign.infrastructure.persistence.campaign_repo import (
    CampaignRepository,
)
from app.contexts.campaign.infrastructure.persistence.lead_repo import LeadRepository
from app.contexts.campaign.infrastructure.persistence.send_job_repo import (
    SendJobRepository,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.poll_inbox import PollInboxHandler
from app.contexts.messaging.application.ports.email_receiver import (
    FetchedMessage,
    FetchResult,
)
from app.contexts.messaging.infrastructure.classifier.deterministic import (
    DeterministicIntentClassifier,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)
from app.contexts.messaging.infrastructure.mailbox.gateway import MailboxGateway
from app.contexts.messaging.infrastructure.persistence.inbound_repo import (
    InboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.outbox_writer import (
    OutboxEventWriter,
)
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)
from app.shared.util.clock import now
from tests.integration.campaign.factories import seed_tenant
from tests.integration.campaign.test_process_send_jobs import (
    FakeGmailSender,
    process_due,
)

FOLLOW_UP_DELAY_SECONDS = 300


class _InboxWithOneReply:
    def __init__(self, reply: FetchedMessage) -> None:
        self._reply = reply

    async def fetch_new(
        self, *, mailbox_email: str, since_cursor: str | None
    ) -> FetchResult:
        return FetchResult(new_cursor="100", messages=(self._reply,))


async def test_a_classified_reply_pauses_the_lead_and_cancels_future_sends(
    session: AsyncSession,
) -> None:
    tenant = await seed_tenant(session)
    started_at = now()

    campaign = await CreateCampaignHandler(
        MailboxLookup(MailboxRepository(session)), CampaignRepository(session)
    ).execute(
        CreateCampaignCommand(
            name="Demo",
            steps=(
                StepDraft(subject="Quick question", body="Hi!", delay_seconds=0),
                StepDraft(
                    subject="Re: Quick question",
                    body="Following up",
                    delay_seconds=FOLLOW_UP_DELAY_SECONDS,
                ),
            ),
        ),
        tenant.workspace_id,
    )
    jobs = SendJobRepository(session)
    await AddLeadsHandler(
        CampaignRepository(session), LeadRepository(session), jobs
    ).execute(campaign.id, ["lead@example.com"], started_at)
    await StartCampaignHandler(
        CampaignRepository(session), LeadRepository(session), jobs
    ).execute(campaign.id, started_at)

    sender = FakeGmailSender()
    await process_due(session, tenant, sender, started_at + timedelta(seconds=1))
    assert sender.sent == [("lead@example.com", "Quick question")]
    first_email = (
        await session.execute(
            select(OutboundMessageRow).where(
                OutboundMessageRow.workspace_id == tenant.workspace_id
            )
        )
    ).scalar_one()

    mailbox_gateway = MailboxGateway(MailboxRepository(session))
    mailbox = await mailbox_gateway.get_by_workspace(tenant.workspace_id)
    assert mailbox is not None
    reply = FetchedMessage(
        provider_message_id="reply-1",
        provider_thread_id="thread-1",
        from_email="lead@example.com",
        subject="Re: Quick question",
        snippet="Yes, interested",
        in_reply_to_header=first_email.rfc822_message_id,
        references_header=first_email.rfc822_message_id,
        received_at=now(),
        body_text="Yes, I'm interested. Let's talk next week.",
    )
    await PollInboxHandler(
        mailbox_gateway,
        OutboundMessageRepository(session),
        InboundMessageRepository(session),
        OutboxEventWriter(session),
        SuppressionRepository(session),
        _InboxWithOneReply(reply),
        DeterministicIntentClassifier(),
    ).run_once(mailbox)

    await HandleClassifiedRepliesHandler(
        ClassifiedReplyFeed(session),
        CampaignRepository(session),
        LeadRepository(session),
        jobs,
    ).run_once(workspace_id=tenant.workspace_id, limit=10, moment=now())

    (lead,) = await LeadRepository(session).list_by_campaign(campaign.id)
    assert (lead.state, lead.stop_reason, lead.reply_intent) == (
        LeadState.PAUSED,
        StopReason.REPLIED,
        "positive",
    )
    statuses = (
        await session.execute(
            select(SendJobRow.status)
            .where(SendJobRow.lead_id == lead.id)
            .order_by(SendJobRow.created_at)
        )
    ).scalars()
    assert list(statuses) == [SendJobStatus.DONE.value, SendJobStatus.CANCELLED.value]

    after_follow_up_delay = started_at + timedelta(seconds=FOLLOW_UP_DELAY_SECONDS + 60)
    assert await process_due(session, tenant, sender, after_follow_up_delay) == []
    assert len(sender.sent) == 1
