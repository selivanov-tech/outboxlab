from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.ports.classified_reply_feed import (
    ClassifiedReply,
)
from app.contexts.campaign.infrastructure.db.models import (
    ProcessedEvent as ProcessedEventRow,
)
from app.contexts.messaging.infrastructure.db.models import (
    OutboxEvent as OutboxEventRow,
)

REPLY_CLASSIFIED = "ReplyClassified"


class ClassifiedReplyFeed:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, workspace_id: UUID, limit: int) -> list[ClassifiedReply]:
        already_processed = exists().where(
            ProcessedEventRow.event_id == OutboxEventRow.id
        )
        stmt = (
            select(
                OutboxEventRow.id, OutboxEventRow.workspace_id, OutboxEventRow.payload
            )
            .where(
                OutboxEventRow.workspace_id == workspace_id,
                OutboxEventRow.event_type == REPLY_CLASSIFIED,
                ~already_processed,
            )
            .order_by(OutboxEventRow.created_at, OutboxEventRow.id)
            .limit(limit)
            .with_for_update(of=OutboxEventRow, skip_locked=True)
        )
        rows = (await self._session.execute(stmt)).all()
        return [_to_reply(row.id, row.workspace_id, row.payload) for row in rows]

    async def acknowledge(self, reply: ClassifiedReply, moment: datetime) -> None:
        await self._session.execute(
            insert(ProcessedEventRow)
            .values(
                event_id=reply.event_id,
                workspace_id=reply.workspace_id,
                processed_at=moment,
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )


def _to_reply(
    event_id: UUID, workspace_id: UUID, payload: dict[str, Any]
) -> ClassifiedReply:
    matched_outbound_id = (
        payload.get("matched_outbound_id")
        if payload.get("event_version", 1) >= 2
        else None
    )
    return ClassifiedReply(
        event_id=event_id,
        workspace_id=workspace_id,
        matched_outbound_id=UUID(matched_outbound_id) if matched_outbound_id else None,
        intent=str(payload["intent"]),
    )
