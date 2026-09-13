from uuid import UUID

from app.contexts.mailbox.application.ports.mailbox_repository import (
    MailboxRepositoryPort,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.messaging.application.ports.mailbox_gateway import MailboxView


class MailboxGateway:
    def __init__(self, mailbox_repo: MailboxRepositoryPort) -> None:
        self._mailbox_repo = mailbox_repo

    async def get_by_workspace(self, workspace_id: UUID) -> MailboxView | None:
        mailbox = await self._mailbox_repo.get_by_workspace(workspace_id)
        return _to_view(mailbox) if mailbox is not None else None

    async def advance_cursor(self, workspace_id: UUID, sync_cursor: str) -> None:
        mailbox = await self._mailbox_repo.get_by_workspace(workspace_id)
        if mailbox is None:
            raise ValueError(f"no mailbox for workspace {workspace_id}")
        await self._mailbox_repo.update_cursor(mailbox.with_cursor(sync_cursor))


def _to_view(mailbox: Mailbox) -> MailboxView:
    return MailboxView(
        id=mailbox.id,
        workspace_id=mailbox.workspace_id,
        email_address=mailbox.email_address,
        last_sync_cursor=mailbox.last_sync_cursor,
        daily_send_cap=mailbox.daily_send_cap,
    )
