from datetime import datetime
from typing import Protocol
from uuid import UUID


class MailboxActivityPort(Protocol):
    async def sent_since(self, mailbox_id: UUID, since: datetime) -> int: ...

    async def suppressed_addresses(self, workspace_id: UUID) -> int: ...
