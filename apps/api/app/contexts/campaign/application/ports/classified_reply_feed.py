from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ClassifiedReply:
    event_id: UUID
    workspace_id: UUID
    matched_outbound_id: UUID | None
    intent: str


class ClassifiedReplyFeedPort(Protocol):
    async def claim(
        self, *, workspace_id: UUID, limit: int
    ) -> list[ClassifiedReply]: ...

    async def acknowledge(self, reply: ClassifiedReply, moment: datetime) -> None: ...
