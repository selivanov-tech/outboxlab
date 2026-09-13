from datetime import timedelta
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.ports.email_dispatch import (
    DispatchDeferred,
    DispatchFailed,
    DispatchResult,
    DispatchSent,
    DispatchSuppressed,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.commands.send_email import (
    DailySendCapReachedError,
    MailboxBusyError,
    MailboxNotConfiguredError,
    RecipientSuppressedError,
    SendEmailCommand,
    SendEmailHandler,
)
from app.contexts.messaging.application.ports.email_sender import EmailSenderPort
from app.config import Settings
from app.contexts.messaging.infrastructure.gmail.access_token import (
    GoogleAccessTokenProvider,
)
from app.contexts.messaging.infrastructure.gmail.sender import GmailApiSender
from app.contexts.messaging.infrastructure.mailbox.gateway import MailboxGateway
from app.contexts.messaging.infrastructure.persistence.mailbox_send_lock import (
    PostgresMailboxSendLock,
)
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)
from app.shared.util.clock import now

BUSY_MAILBOX_RETRY_DELAY = timedelta(seconds=5)


class MessagingEmailDispatch:
    def __init__(self, session: AsyncSession, sender: EmailSenderPort) -> None:
        self._session = session
        self._sender = sender

    async def dispatch(
        self, *, workspace_id: UUID, to_email: str, subject: str, body: str
    ) -> DispatchResult:
        handler = SendEmailHandler(
            MailboxGateway(MailboxRepository(self._session)),
            OutboundMessageRepository(self._session),
            SuppressionRepository(self._session),
            PostgresMailboxSendLock(self._session),
            self._sender,
        )
        command = SendEmailCommand(to_email=to_email, subject=subject, body=body)
        try:
            async with self._session.begin_nested():
                outbound = await handler.execute(command, workspace_id)
        except RecipientSuppressedError:
            return DispatchSuppressed()
        except MailboxBusyError:
            return DispatchDeferred(
                retry_at=now() + BUSY_MAILBOX_RETRY_DELAY, reason="mailbox busy"
            )
        except DailySendCapReachedError as exc:
            return DispatchDeferred(
                retry_at=exc.retry_at, reason="daily send cap reached"
            )
        except MailboxNotConfiguredError:
            return DispatchFailed(error="mailbox not configured")
        except Exception as exc:
            return DispatchFailed(error=f"{exc.__class__.__name__}: {exc}")
        return DispatchSent(
            outbound_message_id=outbound.id, sent_at=outbound.created_at
        )


def gmail_email_dispatch(
    session: AsyncSession, client: httpx.AsyncClient, settings: Settings
) -> MessagingEmailDispatch:
    token_provider = GoogleAccessTokenProvider(
        client,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        refresh_token=settings.google_refresh_token,
    )
    return MessagingEmailDispatch(session, GmailApiSender(client, token_provider))
