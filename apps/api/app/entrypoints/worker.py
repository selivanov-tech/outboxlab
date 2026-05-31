import asyncio
import random
from uuid import UUID

import httpx

from app.config import Settings, get_settings
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.poll_inbox import PollInboxHandler
from app.contexts.messaging.infrastructure.classifier.factory import (
    build_intent_classifier,
)
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)
from app.contexts.messaging.infrastructure.gmail.receiver import GmailApiReceiver
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
from app.contexts.messaging.application.ports.email_receiver import EmailReceiverPort
from app.contexts.messaging.application.ports.intent_classifier import (
    IntentClassifierPort,
)
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.infrastructure.db.session import session_for_workspace


def _log(message: str) -> None:
    print(f"[worker] {message}", flush=True)


def _missing_runtime_config(settings: Settings) -> list[str]:
    required = {
        "GOOGLE_REFRESH_TOKEN": settings.google_refresh_token,
        "GMAIL_USER_EMAIL": settings.gmail_user_email,
        "MAILBOX_WORKSPACE_ID": settings.mailbox_workspace_id,
    }
    return [name for name, value in required.items() if not value]


async def _tick(
    settings: Settings,
    receiver: EmailReceiverPort,
    classifier: IntentClassifierPort,
) -> str:
    missing = _missing_runtime_config(settings)
    if missing:
        return f"missing config {missing}"

    workspace_id = UUID(settings.mailbox_workspace_id)
    try:
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
                receiver,
                classifier,
            )
            processed = await handler.run_once(mailbox)
            if processed:
                _log(f"processed {processed} new reply(ies)")
    except Exception as exc:
        _log(f"poll error ({exc.__class__.__name__}): {exc}")
    return ""


async def _run() -> None:
    settings = get_settings()
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
            classifier = build_intent_classifier(settings, client)
            while True:
                idle_reason = await _tick(settings, receiver, classifier)
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
