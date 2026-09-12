from typing import Any

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
from app.contexts.messaging.application.poll_inbox import PollInboxHandler
from app.contexts.messaging.application.ports.email_receiver import (
    FetchedMessage,
    FetchResult,
)
from app.contexts.messaging.application.ports.mailbox_gateway import MailboxView
from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.infrastructure.db.models import (
    InboundMessage as InboundMessageRow,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboxEvent as OutboxEventRow,
)
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
from app.shared.util.clock import now


class _FakeReceiver:
    def __init__(self, result: FetchResult) -> None:
        self._result = result
        self.since: list[str | None] = []

    async def fetch_new(
        self, *, mailbox_email: str, since_cursor: str | None
    ) -> FetchResult:
        self.since.append(since_cursor)
        return self._result


class _FakeClassifier:
    def __init__(self, intent: Intent) -> None:
        self._intent = intent
        self.calls: list[tuple[str, str]] = []

    async def classify(self, subject: str, text: str) -> Intent:
        self.calls.append((subject, text))
        return self._intent


def _fetched(**overrides: Any) -> FetchedMessage:
    defaults: dict[str, Any] = {
        "provider_message_id": "g1",
        "provider_thread_id": "thread-1",
        "from_email": "lead@example.com",
        "subject": "Re: Hi",
        "snippet": "yes interested",
        "in_reply_to_header": None,
        "references_header": None,
        "received_at": now(),
    }
    defaults.update(overrides)
    return FetchedMessage(**defaults)


async def _seed_mailbox(session: AsyncSession) -> MailboxView:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)
    await MailboxRepository(session).add(Mailbox.new(ws.id, "ops@example.com"))
    view = await MailboxGateway(MailboxRepository(session)).get_by_workspace(ws.id)
    assert view is not None
    return view


def _handler(
    session: AsyncSession, receiver: _FakeReceiver, classifier: _FakeClassifier
) -> PollInboxHandler:
    return PollInboxHandler(
        MailboxGateway(MailboxRepository(session)),
        OutboundMessageRepository(session),
        InboundMessageRepository(session),
        OutboxEventWriter(session),
        receiver,
        classifier,
    )


async def _event_types(session: AsyncSession) -> list[str]:
    return list(
        (
            await session.execute(
                select(OutboxEventRow.event_type).order_by(
                    OutboxEventRow.created_at, OutboxEventRow.id
                )
            )
        )
        .scalars()
        .all()
    )


async def test_matched_reply_emits_three_events_in_order(
    session: AsyncSession,
) -> None:
    mailbox = await _seed_mailbox(session)
    out_repo = OutboundMessageRepository(session)
    outbound = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id="<m1@example.com>",
    )
    await out_repo.add(outbound)
    await out_repo.mark_sent(outbound.sent("gmail-out", "thread-1"))

    reply = _fetched(
        provider_message_id="g-reply",
        provider_thread_id="thread-1",
        in_reply_to_header="<m1@example.com>",
    )
    receiver = _FakeReceiver(FetchResult(new_cursor="6000", messages=(reply,)))
    classifier = _FakeClassifier(Intent.POSITIVE)

    processed = await _handler(session, receiver, classifier).run_once(mailbox)

    assert processed == 1
    inbound_row = (await session.execute(select(InboundMessageRow))).scalars().one()
    assert inbound_row.matched_outbound_id == outbound.id
    assert inbound_row.intent == "positive"
    assert classifier.calls == [("Re: Hi", "yes interested")]
    assert await _event_types(session) == [
        "InboundReceived",
        "ReplyMatched",
        "ReplyClassified",
    ]

    refreshed = await MailboxRepository(session).get_by_workspace(mailbox.workspace_id)
    assert refreshed is not None
    assert refreshed.last_sync_cursor == "6000"


async def test_classifier_uses_body_text_over_snippet(
    session: AsyncSession,
) -> None:
    mailbox = await _seed_mailbox(session)
    out_repo = OutboundMessageRepository(session)
    outbound = OutboundMessage.new(
        workspace_id=mailbox.workspace_id,
        mailbox_id=mailbox.id,
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id="<m1@example.com>",
    )
    await out_repo.add(outbound)
    await out_repo.mark_sent(outbound.sent("gmail-out", "thread-1"))

    reply = _fetched(
        provider_message_id="g-reply",
        provider_thread_id="thread-1",
        in_reply_to_header="<m1@example.com>",
        snippet="our pitch: book a call, interested?",
        body_text="Thanks, not interested.",
    )
    receiver = _FakeReceiver(FetchResult(new_cursor="6000", messages=(reply,)))
    classifier = _FakeClassifier(Intent.NEGATIVE)

    await _handler(session, receiver, classifier).run_once(mailbox)

    assert classifier.calls == [("Re: Hi", "Thanks, not interested.")]


async def test_unmatched_reply_emits_only_inbound_received(
    session: AsyncSession,
) -> None:
    mailbox = await _seed_mailbox(session)
    reply = _fetched(
        provider_message_id="g-x",
        provider_thread_id="thread-x",
        from_email="stranger@example.com",
        subject="Random question",
        in_reply_to_header=None,
    )
    receiver = _FakeReceiver(FetchResult(new_cursor="6001", messages=(reply,)))
    classifier = _FakeClassifier(Intent.POSITIVE)

    processed = await _handler(session, receiver, classifier).run_once(mailbox)

    assert processed == 1
    inbound_row = (await session.execute(select(InboundMessageRow))).scalars().one()
    assert inbound_row.matched_outbound_id is None
    assert inbound_row.intent is None
    assert await _event_types(session) == ["InboundReceived"]
    assert classifier.calls == []


async def test_dedupe_on_second_run(
    session: AsyncSession,
) -> None:
    mailbox = await _seed_mailbox(session)
    keep = _fetched(provider_message_id="g1")
    receiver = _FakeReceiver(FetchResult(new_cursor="7000", messages=(keep,)))
    classifier = _FakeClassifier(Intent.UNCLEAR)

    processed = await _handler(session, receiver, classifier).run_once(mailbox)

    assert processed == 1
    stored = (
        (await session.execute(select(InboundMessageRow.provider_message_id)))
        .scalars()
        .all()
    )
    assert list(stored) == ["g1"]

    refreshed = await MailboxGateway(MailboxRepository(session)).get_by_workspace(
        mailbox.workspace_id
    )
    assert refreshed is not None
    receiver2 = _FakeReceiver(FetchResult(new_cursor="7001", messages=(keep,)))
    processed_again = await _handler(session, receiver2, classifier).run_once(refreshed)

    assert processed_again == 0
    stored_again = (
        (await session.execute(select(InboundMessageRow.provider_message_id)))
        .scalars()
        .all()
    )
    assert list(stored_again) == ["g1"]
