from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.ports.email_dispatch import (
    DispatchFailed,
    DispatchResult,
    DispatchSent,
)
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.commands.send_email import (
    MailboxNotConfiguredError,
    SendEmailCommand,
    SendEmailHandler,
)
from app.contexts.messaging.application.ports.email_sender import EmailSenderPort
from app.contexts.messaging.infrastructure.mailbox.gateway import MailboxGateway
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)


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
            self._sender,
        )
        command = SendEmailCommand(to_email=to_email, subject=subject, body=body)
        try:
            async with self._session.begin_nested():
                outbound = await handler.execute(command, workspace_id)
        except MailboxNotConfiguredError:
            return DispatchFailed(error="mailbox not configured")
        except httpx.HTTPError as exc:
            return DispatchFailed(error=f"{exc.__class__.__name__}: {exc}")
        return DispatchSent(
            outbound_message_id=outbound.id, sent_at=outbound.created_at
        )
