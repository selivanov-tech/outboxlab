from typing import Protocol
from uuid import UUID


class MailboxSendLockPort(Protocol):
    async def try_acquire(self, mailbox_id: UUID) -> bool: ...
