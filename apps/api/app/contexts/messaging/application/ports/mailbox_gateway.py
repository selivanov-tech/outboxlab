from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class MailboxView:
    id: UUID
    workspace_id: UUID
    email_address: str
    last_sync_cursor: str | None


class MailboxGatewayPort(Protocol):
    async def get_by_workspace(self, workspace_id: UUID) -> MailboxView | None: ...

    async def advance_cursor(self, workspace_id: UUID, sync_cursor: str) -> None: ...
