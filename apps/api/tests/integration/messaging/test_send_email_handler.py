import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.application.commands.send_email import (
    MailboxNotConfiguredError,
    SendEmailCommand,
    SendEmailHandler,
)
from app.contexts.messaging.application.ports.email_sender import SentEmail
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)
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


class _FakeSender:
    def __init__(self) -> None:
        self.sent_rfc822_ids: list[str] = []

    async def send(
        self,
        *,
        mailbox_email: str,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> SentEmail:
        self.sent_rfc822_ids.append(rfc822_message_id)
        return SentEmail(provider_message_id="gmail-1", provider_thread_id="thread-1")


async def _seed_workspace(session: AsyncSession) -> Workspace:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)
    return ws


async def test_persists_outbound_and_marks_sent(session: AsyncSession) -> None:
    ws = await _seed_workspace(session)
    await MailboxRepository(session).add(Mailbox.new(ws.id, "ops@example.com"))
    sender = _FakeSender()
    handler = SendEmailHandler(
        MailboxGateway(MailboxRepository(session)),
        OutboundMessageRepository(session),
        SuppressionRepository(session),
        PostgresMailboxSendLock(session),
        sender,
    )

    result = await handler.execute(
        SendEmailCommand(to_email="lead@example.com", subject="Hi", body="Body"),
        ws.id,
    )

    assert result.provider_message_id == "gmail-1"
    assert result.provider_thread_id == "thread-1"

    row = (
        (
            await session.execute(
                select(OutboundMessageRow).where(
                    OutboundMessageRow.workspace_id == ws.id
                )
            )
        )
        .scalars()
        .one()
    )
    assert row.rfc822_message_id == sender.sent_rfc822_ids[0]
    assert row.rfc822_message_id.endswith("@example.com>")
    assert row.provider_message_id == "gmail-1"
    assert row.provider_thread_id == "thread-1"


async def test_raises_when_mailbox_not_configured(session: AsyncSession) -> None:
    ws = await _seed_workspace(session)
    handler = SendEmailHandler(
        MailboxGateway(MailboxRepository(session)),
        OutboundMessageRepository(session),
        SuppressionRepository(session),
        PostgresMailboxSendLock(session),
        _FakeSender(),
    )

    with pytest.raises(MailboxNotConfiguredError):
        await handler.execute(
            SendEmailCommand(to_email="lead@example.com", subject="s", body="b"),
            ws.id,
        )
