from typing import Protocol
from uuid import UUID


class OutboxEventWriterPort(Protocol):
    async def record(
        self,
        event_type: str,
        workspace_id: UUID,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None: ...
