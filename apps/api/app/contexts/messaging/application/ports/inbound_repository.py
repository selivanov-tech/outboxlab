from typing import Protocol
from uuid import UUID

from app.contexts.messaging.domain.inbound_message import InboundMessage


class InboundMessageRepositoryPort(Protocol):
    async def add(self, message: InboundMessage) -> None: ...

    async def update(self, message: InboundMessage) -> None: ...

    async def exists(self, mailbox_id: UUID, provider_message_id: str) -> bool: ...
