from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.messaging.domain.inbound_message import InboundMessage
from app.contexts.messaging.domain.intent import Intent
from app.contexts.messaging.infrastructure.db.models import (
    InboundMessage as InboundMessageRow,
)


class InboundMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: InboundMessage) -> None:
        self._session.add(_to_row(message))
        await self._session.flush()

    async def update(self, message: InboundMessage) -> None:
        row = await self._session.get(InboundMessageRow, message.id)
        if row is None:
            raise ValueError(f"inbound message {message.id} not found")
        row.matched_outbound_id = message.matched_outbound_id
        row.intent = message.intent.value if message.intent is not None else None
        await self._session.flush()

    async def exists(self, mailbox_id: UUID, provider_message_id: str) -> bool:
        stmt = (
            select(InboundMessageRow.id)
            .where(
                InboundMessageRow.mailbox_id == mailbox_id,
                InboundMessageRow.provider_message_id == provider_message_id,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None


def _to_row(message: InboundMessage) -> InboundMessageRow:
    return InboundMessageRow(
        id=message.id,
        workspace_id=message.workspace_id,
        mailbox_id=message.mailbox_id,
        provider_message_id=message.provider_message_id,
        provider_thread_id=message.provider_thread_id,
        from_email=message.from_email,
        subject=message.subject,
        snippet=message.snippet,
        in_reply_to_header=message.in_reply_to_header,
        references_header=message.references_header,
        matched_outbound_id=message.matched_outbound_id,
        intent=message.intent.value if message.intent is not None else None,
        received_at=message.received_at,
        created_at=message.created_at,
    )


def _to_domain(row: InboundMessageRow) -> InboundMessage:
    return InboundMessage(
        id=row.id,
        workspace_id=row.workspace_id,
        mailbox_id=row.mailbox_id,
        provider_message_id=row.provider_message_id,
        provider_thread_id=row.provider_thread_id,
        from_email=row.from_email,
        subject=row.subject,
        snippet=row.snippet,
        in_reply_to_header=row.in_reply_to_header,
        references_header=row.references_header,
        matched_outbound_id=row.matched_outbound_id,
        intent=Intent(row.intent) if row.intent is not None else None,
        received_at=row.received_at,
        created_at=row.created_at,
    )
