from uuid import UUID

from app.contexts.mailbox.application.ports.mailbox_repository import (
    MailboxRepositoryPort,
)


class MailboxLookup:
    def __init__(self, mailbox_repo: MailboxRepositoryPort) -> None:
        self._mailbox_repo = mailbox_repo

    async def mailbox_id_for(self, workspace_id: UUID) -> UUID | None:
        mailbox = await self._mailbox_repo.get_by_workspace(workspace_id)
        return mailbox.id if mailbox is not None else None
