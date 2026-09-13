from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.contexts.messaging.application.message_id import make_message_id
from app.contexts.messaging.application.ports.email_sender import EmailSenderPort
from app.contexts.messaging.application.ports.mailbox_gateway import MailboxGatewayPort
from app.contexts.messaging.application.ports.mailbox_send_lock import (
    MailboxSendLockPort,
)
from app.contexts.messaging.application.ports.outbound_repository import (
    OutboundMessageRepositoryPort,
)
from app.contexts.messaging.application.ports.suppression_repository import (
    SuppressionRepositoryPort,
)
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.shared.util.clock import now, start_of_utc_day


class MailboxNotConfiguredError(Exception):
    pass


class RecipientSuppressedError(Exception):
    pass


class MailboxBusyError(Exception):
    pass


class DailySendCapReachedError(Exception):
    def __init__(self, retry_at: datetime) -> None:
        super().__init__(f"Daily send cap reached, retry at {retry_at.isoformat()}")
        self.retry_at = retry_at


@dataclass(frozen=True)
class SendEmailCommand:
    to_email: str
    subject: str
    body: str


class SendEmailHandler:
    def __init__(
        self,
        mailbox_gateway: MailboxGatewayPort,
        outbound_repo: OutboundMessageRepositoryPort,
        suppressions: SuppressionRepositoryPort,
        send_lock: MailboxSendLockPort,
        sender: EmailSenderPort,
    ) -> None:
        self._mailbox_gateway = mailbox_gateway
        self._outbound_repo = outbound_repo
        self._suppressions = suppressions
        self._send_lock = send_lock
        self._sender = sender

    async def execute(
        self, command: SendEmailCommand, workspace_id: UUID
    ) -> OutboundMessage:
        mailbox = await self._mailbox_gateway.get_by_workspace(workspace_id)
        if mailbox is None:
            raise MailboxNotConfiguredError
        if await self._suppressions.is_suppressed(workspace_id, command.to_email):
            raise RecipientSuppressedError
        if not await self._send_lock.try_acquire(mailbox.id):
            raise MailboxBusyError
        day_start = start_of_utc_day(now())
        sent_today = await self._outbound_repo.count_sent_since(mailbox.id, day_start)
        if sent_today >= mailbox.daily_send_cap:
            raise DailySendCapReachedError(day_start + timedelta(days=1))

        rfc822_message_id = make_message_id(mailbox.email_address.split("@")[-1])
        outbound = OutboundMessage.new(
            workspace_id=workspace_id,
            mailbox_id=mailbox.id,
            to_email=command.to_email,
            subject=command.subject,
            body=command.body,
            rfc822_message_id=rfc822_message_id,
        )
        await self._outbound_repo.add(outbound)

        sent = await self._sender.send(
            mailbox_email=mailbox.email_address,
            to_email=command.to_email,
            subject=command.subject,
            body=command.body,
            rfc822_message_id=rfc822_message_id,
        )
        delivered = outbound.sent(sent.provider_message_id, sent.provider_thread_id)
        await self._outbound_repo.mark_sent(delivered)
        return delivered
