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
from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.infrastructure.db.models import (
    InboundMessage as InboundMessageRow,
)
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


def _new_inbound(mailbox: Mailbox) -> InboundMessage:
    return InboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        provider_message_id="g1",
        provider_thread_id="t1",
        from_email="lead@example.com",
        subject="Re: Hi",
        snippet="yes, interested",
        in_reply_to_header="<m1@example.com>",
        references_header=None,
        received_at=now(),
    )


async def test_exists_reflects_add(session: AsyncSession) -> None:
    mailbox = await _seed_mailbox(session)
    repo = InboundMessageRepository(session)

    assert await repo.exists(mailbox.id, "g1") is False
    await repo.add(_new_inbound(mailbox))
    assert await repo.exists(mailbox.id, "g1") is True


async def test_update_persists_match_and_intent(session: AsyncSession) -> None:
    mailbox = await _seed_mailbox(session)
    outbound = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id="<m1@example.com>",
    )
    await OutboundMessageRepository(session).add(outbound)

    repo = InboundMessageRepository(session)
    inbound = _new_inbound(mailbox)
    await repo.add(inbound)
    await repo.update(inbound.matched_to(outbound.id).classified_as(Intent.POSITIVE))

    row = await session.get(InboundMessageRow, inbound.id)
    assert row is not None
    assert row.matched_outbound_id == outbound.id
    assert row.intent == "positive"
