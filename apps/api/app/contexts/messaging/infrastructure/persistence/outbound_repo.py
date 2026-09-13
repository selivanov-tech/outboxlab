from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.infrastructure.db.models import (
    InboundMessage as InboundMessageRow,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)

_CANDIDATE_LIMIT = 100


class OutboundMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: OutboundMessage) -> None:
        self._session.add(_to_row(message))
        await self._session.flush()

    async def mark_sent(self, message: OutboundMessage) -> None:
        row = await self._session.get(OutboundMessageRow, message.id)
        if row is None:
            raise ValueError(f"outbound message {message.id} not found")
        row.provider_message_id = message.provider_message_id
        row.provider_thread_id = message.provider_thread_id
        await self._session.flush()

    async def list_unanswered(self, mailbox_id: UUID) -> list[OutboundMessage]:
        answered = exists().where(
            InboundMessageRow.matched_outbound_id == OutboundMessageRow.id
        )
        stmt = (
            select(OutboundMessageRow)
            .where(
                OutboundMessageRow.mailbox_id == mailbox_id,
                OutboundMessageRow.provider_message_id.is_not(None),
                ~answered,
            )
            .order_by(OutboundMessageRow.created_at.desc())
            .limit(_CANDIDATE_LIMIT)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def count_sent_since(self, mailbox_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(OutboundMessageRow)
            .where(
                OutboundMessageRow.mailbox_id == mailbox_id,
                OutboundMessageRow.provider_message_id.is_not(None),
                OutboundMessageRow.created_at >= since,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())


def _to_domain(row: OutboundMessageRow) -> OutboundMessage:
    return OutboundMessage(
        id=row.id,
        workspace_id=row.workspace_id,
        mailbox_id=row.mailbox_id,
        to_email=row.to_email,
        subject=row.subject,
        body=row.body,
        rfc822_message_id=row.rfc822_message_id,
        provider_message_id=row.provider_message_id,
        provider_thread_id=row.provider_thread_id,
        created_at=row.created_at,
    )


def _to_row(message: OutboundMessage) -> OutboundMessageRow:
    return OutboundMessageRow(
        id=message.id,
        workspace_id=message.workspace_id,
        mailbox_id=message.mailbox_id,
        to_email=message.to_email,
        subject=message.subject,
        body=message.body,
        rfc822_message_id=message.rfc822_message_id,
        provider_message_id=message.provider_message_id,
        provider_thread_id=message.provider_thread_id,
        created_at=message.created_at,
    )
