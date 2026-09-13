from typing import Protocol
from uuid import UUID

from app.contexts.mailbox.domain.mailbox import Mailbox


class MailboxRepositoryPort(Protocol):
    async def get_by_workspace(self, workspace_id: UUID) -> Mailbox | None: ...

    async def list_by_workspace(self, workspace_id: UUID) -> list[Mailbox]: ...

    async def update_cursor(self, mailbox: Mailbox) -> None: ...
