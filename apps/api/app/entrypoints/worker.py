import asyncio
import os
import random
import socket
from uuid import UUID

import httpx

from app.config import Settings, get_settings
from app.contexts.campaign.application.handle_classified_replies import (
    HandleClassifiedRepliesHandler,
)
from app.contexts.campaign.application.process_send_jobs import (
    ClaimDueSendJobsHandler,
    ProcessClaimedSendJobHandler,
)
from app.contexts.campaign.infrastructure.messaging.email_dispatch import (
    MessagingEmailDispatch,
)
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
from app.contexts.messaging.application.ports.email_receiver import EmailReceiverPort
from app.contexts.messaging.application.ports.email_sender import EmailSenderPort
from app.contexts.messaging.application.ports.intent_classifier import (
    IntentClassifierPort,
)
from app.contexts.messaging.infrastructure.classifier.factory import (
    build_intent_classifier,
)
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)
from app.contexts.messaging.infrastructure.gmail.receiver import GmailApiReceiver
from app.contexts.messaging.infrastructure.gmail.sender import GmailApiSender
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
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.infrastructure.db.session import session_for_workspace
from app.shared.util.clock import now

SEND_BATCH_SIZE = 10
REPLY_BATCH_SIZE = 50


def _log(message: str) -> None:
    print(f"[worker] {message}", flush=True)


def _worker_id() -> str:
    return f"python-{socket.gethostname()}-{os.getpid()}"


def _missing_runtime_config(settings: Settings) -> list[str]:
    required = {
        "GOOGLE_REFRESH_TOKEN": settings.google_refresh_token,
        "GMAIL_USER_EMAIL": settings.gmail_user_email,
        "MAILBOX_WORKSPACE_ID": settings.mailbox_workspace_id,
    }
    return [name for name, value in required.items() if not value]


async def _poll_inbox(
    workspace_id: UUID,
    receiver: EmailReceiverPort,
    classifier: IntentClassifierPort,
) -> str:
    async with session_for_workspace(workspace_id) as session:
        mailbox_gateway = MailboxGateway(MailboxRepository(session))
        mailbox = await mailbox_gateway.get_by_workspace(workspace_id)
        if mailbox is None:
            return f"no mailbox seeded for workspace {workspace_id}"
        handler = PollInboxHandler(
            mailbox_gateway,
            OutboundMessageRepository(session),
            InboundMessageRepository(session),
            OutboxEventWriter(session),
            SuppressionRepository(session),
            receiver,
            classifier,
        )
        processed = await handler.run_once(mailbox)
    if processed:
        _log(f"processed {processed} new reply(ies)")
    return ""


async def _dispatch_classified_replies(workspace_id: UUID) -> None:
    async with session_for_workspace(workspace_id) as session:
        stopped = await HandleClassifiedRepliesHandler(
            ClassifiedReplyFeed(session),
            CampaignRepository(session),
            LeadRepository(session),
            SendJobRepository(session),
        ).run_once(workspace_id=workspace_id, limit=REPLY_BATCH_SIZE, moment=now())
    for lead in stopped:
        _log(
            f"lead {lead.id} is {lead.state} ({lead.stop_reason}, "
            f"intent {lead.reply_intent}); future sends cancelled"
        )


async def _drain_send_jobs(
    workspace_id: UUID, sender: EmailSenderPort, worker_id: str
) -> None:
    async with session_for_workspace(workspace_id) as session:
        jobs = await ClaimDueSendJobsHandler(SendJobRepository(session)).execute(
            workspace_id=workspace_id,
            worker_id=worker_id,
            limit=SEND_BATCH_SIZE,
            moment=now(),
        )
    for job in jobs:
        async with session_for_workspace(workspace_id) as session:
            handler = ProcessClaimedSendJobHandler(
                CampaignRepository(session),
                LeadRepository(session),
                SendJobRepository(session),
                MessagingEmailDispatch(session, sender),
            )
            outcome = await handler.execute(job, now())
        _log(
            f"send job {job.id} (lead {job.lead_id}, step "
            f"{job.payload.step_position}): {outcome}"
        )


async def _tick(
    settings: Settings,
    receiver: EmailReceiverPort,
    classifier: IntentClassifierPort,
    sender: EmailSenderPort,
    worker_id: str,
) -> str:
    missing = _missing_runtime_config(settings)
    if missing:
        return f"missing config {missing}"

    workspace_id = UUID(settings.mailbox_workspace_id)
    idle_reason = ""
    try:
        idle_reason = await _poll_inbox(workspace_id, receiver, classifier)
    except Exception as exc:
        _log(f"poll error ({exc.__class__.__name__}): {exc}")
    try:
        await _dispatch_classified_replies(workspace_id)
    except Exception as exc:
        _log(f"reply dispatch error ({exc.__class__.__name__}): {exc}")
    try:
        await _drain_send_jobs(workspace_id, sender, worker_id)
    except Exception as exc:
        _log(f"send error ({exc.__class__.__name__}): {exc}")
    return idle_reason


async def _run() -> None:
    settings = get_settings()
    worker_id = _worker_id()
    last_idle: str | None = None
    try:
        async with httpx.AsyncClient() as client:
            token_provider = GoogleAccessTokenProvider(
                client,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                refresh_token=settings.google_refresh_token,
            )
            receiver = GmailApiReceiver(client, token_provider)
            sender = GmailApiSender(client, token_provider)
            classifier = build_intent_classifier(settings, client)
            _log(
                "loops: poll inbox -> dispatch classified replies -> drain send jobs; "
                f"workspace {settings.mailbox_workspace_id or 'not set'}; "
                f"classifier {classifier.__class__.__name__}"
            )
            while True:
                idle_reason = await _tick(
                    settings, receiver, classifier, sender, worker_id
                )
                if idle_reason != last_idle:
                    if idle_reason:
                        _log(f"idle: {idle_reason}")
                    last_idle = idle_reason
                delay = settings.poll_interval_seconds + random.uniform(
                    0, settings.poll_jitter_seconds
                )
                await asyncio.sleep(delay)
    finally:
        await dispose_engine()


def main() -> None:
    _log(f"starting (APP_ENV={get_settings().app_env})")
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        _log("stopped")


if __name__ == "__main__":
    main()
