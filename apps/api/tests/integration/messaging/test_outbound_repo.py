from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)
from app.contexts.messaging.domain.inbound_message import InboundMessage
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.infrastructure.persistence.inbound_repo import (
    InboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.shared.util.clock import now


async def _seed_mailbox(session: AsyncSession) -> Mailbox:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)
    mailbox = Mailbox.new(ws.id, "ops@example.com")
    await MailboxRepository(session).add(mailbox)
    return mailbox


def _new_outbound(mailbox: Mailbox, rfc822_message_id: str) -> OutboundMessage:
    return OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id=rfc822_message_id,
    )


async def test_unsent_message_is_not_a_candidate(session: AsyncSession) -> None:
    mailbox = await _seed_mailbox(session)
    repo = OutboundMessageRepository(session)
    await repo.add(_new_outbound(mailbox, "<m1@example.com>"))

    assert await repo.list_unanswered(mailbox.id) == []


async def test_mark_sent_then_listed_unanswered(session: AsyncSession) -> None:
    mailbox = await _seed_mailbox(session)
    repo = OutboundMessageRepository(session)
    outbound = _new_outbound(mailbox, "<m1@example.com>")
    await repo.add(outbound)

    await repo.mark_sent(outbound.sent("gmail-1", "thread-1"))

    unanswered = await repo.list_unanswered(mailbox.id)
    assert [m.id for m in unanswered] == [outbound.id]
    assert unanswered[0].provider_message_id == "gmail-1"
    assert unanswered[0].provider_thread_id == "thread-1"


async def test_answered_message_is_excluded(session: AsyncSession) -> None:
    mailbox = await _seed_mailbox(session)
    out_repo = OutboundMessageRepository(session)
    outbound = _new_outbound(mailbox, "<m1@example.com>")
    await out_repo.add(outbound)
    await out_repo.mark_sent(outbound.sent("gmail-1", "thread-1"))

    in_repo = InboundMessageRepository(session)
    reply = InboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        provider_message_id="g-reply",
        provider_thread_id="thread-1",
        from_email="lead@example.com",
        subject="Re: Hi",
        snippet="interested",
        in_reply_to_header="<m1@example.com>",
        references_header=None,
        received_at=now(),
    )
    await in_repo.add(reply)
    await in_repo.update(reply.matched_to(outbound.id))

    assert await out_repo.list_unanswered(mailbox.id) == []
