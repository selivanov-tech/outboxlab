from dataclasses import dataclass
from uuid import UUID

from app.contexts.messaging.application.message_id import make_message_id
from app.contexts.messaging.application.ports.email_sender import EmailSenderPort
from app.contexts.messaging.application.ports.mailbox_gateway import MailboxGatewayPort
from app.contexts.messaging.application.ports.outbound_repository import (
    OutboundMessageRepositoryPort,
)
from app.contexts.messaging.domain.outbound_message import OutboundMessage


class MailboxNotConfiguredError(Exception):
    pass


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
        sender: EmailSenderPort,
    ) -> None:
        self._mailbox_gateway = mailbox_gateway
        self._outbound_repo = outbound_repo
        self._sender = sender

    async def execute(
        self, command: SendEmailCommand, workspace_id: UUID
    ) -> OutboundMessage:
        mailbox = await self._mailbox_gateway.get_by_workspace(workspace_id)
        if mailbox is None:
            raise MailboxNotConfiguredError

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
