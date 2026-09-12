import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.messaging.infrastructure.db.models import (
    OutboxEvent as OutboxEventRow,
)
from app.shared.util.clock import now


class OutboxEventWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        event_type: str,
        workspace_id: UUID,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None:
        body = _json_safe({**payload, "event_type": event_type})
        self._session.add(
            OutboxEventRow(
                id=uuid.uuid7(),
                workspace_id=workspace_id,
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload=body,
                created_at=now(),
            )
        )
        await self._session.flush()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
