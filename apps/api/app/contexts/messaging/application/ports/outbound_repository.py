from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.contexts.messaging.domain.outbound_message import OutboundMessage


class OutboundMessageRepositoryPort(Protocol):
    async def add(self, message: OutboundMessage) -> None: ...

    async def mark_sent(self, message: OutboundMessage) -> None: ...

    async def list_unanswered(self, mailbox_id: UUID) -> list[OutboundMessage]: ...

    async def count_sent_since(self, mailbox_id: UUID, since: datetime) -> int: ...
