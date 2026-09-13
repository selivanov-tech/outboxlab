from typing import Protocol
from uuid import UUID


class MailboxLookupPort(Protocol):
    async def mailbox_id_for(self, workspace_id: UUID) -> UUID | None: ...
