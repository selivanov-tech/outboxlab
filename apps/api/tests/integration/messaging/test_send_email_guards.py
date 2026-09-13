from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.commands.send_email import (
    DailySendCapReachedError,
    MailboxBusyError,
    RecipientSuppressedError,
    SendEmailCommand,
    SendEmailHandler,
)
from app.contexts.messaging.application.ports.email_sender import SentEmail
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.domain.suppression import Suppression, SuppressionReason
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
from app.shared.util.clock import now, start_of_utc_day


class _RecordingSender:
    def __init__(self) -> None:
        self.sent_to: list[str] = []

    async def send(
        self,
        *,
        mailbox_email: str,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> SentEmail:
        self.sent_to.append(to_email)
        return SentEmail(
            provider_message_id=f"gmail-{len(self.sent_to)}",
            provider_thread_id="thread",
        )


async def _mailbox(session: AsyncSession, daily_send_cap: int = 20) -> Mailbox:
    workspace = Workspace.new("acme")
    await WorkspaceRepository(session).add(workspace)
    mailbox = Mailbox.new(workspace.id, "ops@example.com", daily_send_cap)
    await MailboxRepository(session).add(mailbox)
    return mailbox


def _handler(session: AsyncSession, sender: _RecordingSender) -> SendEmailHandler:
    return SendEmailHandler(
        MailboxGateway(MailboxRepository(session)),
        OutboundMessageRepository(session),
        SuppressionRepository(session),
        PostgresMailboxSendLock(session),
        sender,
    )


def _command(to_email: str = "lead@example.com") -> SendEmailCommand:
    return SendEmailCommand(to_email=to_email, subject="Hi", body="Body")


async def test_suppressed_recipient_is_not_sent(session: AsyncSession) -> None:
    mailbox = await _mailbox(session)
    await SuppressionRepository(session).add(
        Suppression.new(
            workspace_id=mailbox.workspace_id,
            email="lead@example.com",
            reason=SuppressionReason.UNSUBSCRIBE,
            source_inbound_id=None,
        )
    )
    sender = _RecordingSender()

    with pytest.raises(RecipientSuppressedError):
        await _handler(session, sender).execute(_command(), mailbox.workspace_id)

    assert sender.sent_to == []


async def test_daily_cap_blocks_sends_until_the_next_utc_day(
    session: AsyncSession,
) -> None:
    mailbox = await _mailbox(session, daily_send_cap=1)
    sender = _RecordingSender()
    handler = _handler(session, sender)
    await handler.execute(_command("first@example.com"), mailbox.workspace_id)

    with pytest.raises(DailySendCapReachedError) as raised:
        await handler.execute(_command("second@example.com"), mailbox.workspace_id)

    assert sender.sent_to == ["first@example.com"]
    assert raised.value.retry_at == start_of_utc_day(now()) + timedelta(days=1)


async def test_unsent_and_older_messages_do_not_count_toward_the_cap(
    session: AsyncSession,
) -> None:
    mailbox = await _mailbox(session, daily_send_cap=1)
    outbound_repo = OutboundMessageRepository(session)
    unsent = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="unsent@example.com",
        subject="s",
        body="b",
        rfc822_message_id="<unsent@example.com>",
    )
    yesterday = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="old@example.com",
        subject="s",
        body="b",
        rfc822_message_id="<old@example.com>",
    ).model_copy(update={"created_at": start_of_utc_day(now()) - timedelta(hours=1)})
    await outbound_repo.add(unsent)
    await outbound_repo.add(yesterday)
    await outbound_repo.mark_sent(yesterday.sent("gmail-old", "thread-old"))
    sender = _RecordingSender()

    await _handler(session, sender).execute(_command(), mailbox.workspace_id)

    assert sender.sent_to == ["lead@example.com"]


async def test_mailbox_locked_by_another_sender_is_busy(
    session: AsyncSession, engine: AsyncEngine
) -> None:
    mailbox = await _mailbox(session)
    sender = _RecordingSender()
    lock_key = {"key": str(mailbox.id)}

    async with engine.connect() as other_sender:
        await other_sender.execute(
            text("SELECT pg_advisory_lock(hashtext(:key))"), lock_key
        )
        try:
            with pytest.raises(MailboxBusyError):
                await _handler(session, sender).execute(
                    _command(), mailbox.workspace_id
                )
        finally:
            await other_sender.execute(
                text("SELECT pg_advisory_unlock(hashtext(:key))"), lock_key
            )

    assert sender.sent_to == []
