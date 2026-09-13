from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.db.models import Mailbox as MailboxRow


class MailboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_workspace(self, workspace_id: UUID) -> Mailbox | None:
        stmt = (
            select(MailboxRow)
            .where(MailboxRow.workspace_id == workspace_id)
            .order_by(MailboxRow.created_at)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return _to_domain(row) if row is not None else None

    async def list_by_workspace(self, workspace_id: UUID) -> list[Mailbox]:
        stmt = (
            select(MailboxRow)
            .where(MailboxRow.workspace_id == workspace_id)
            .order_by(MailboxRow.created_at, MailboxRow.id)
        )
        return [
            _to_domain(row) for row in (await self._session.execute(stmt)).scalars()
        ]

    async def add(self, mailbox: Mailbox) -> None:
        self._session.add(_to_row(mailbox))
        await self._session.flush()

    async def update_cursor(self, mailbox: Mailbox) -> None:
        row = await self._session.get(MailboxRow, mailbox.id)
        if row is None:
            raise ValueError(f"mailbox {mailbox.id} not found")
        row.last_sync_cursor = mailbox.last_sync_cursor
        await self._session.flush()


def _to_domain(row: MailboxRow) -> Mailbox:
    return Mailbox(
        id=row.id,
        workspace_id=row.workspace_id,
        email_address=row.email_address,
        last_sync_cursor=row.last_sync_cursor,
        daily_send_cap=row.daily_send_cap,
        created_at=row.created_at,
    )


def _to_row(mailbox: Mailbox) -> MailboxRow:
    return MailboxRow(
        id=mailbox.id,
        workspace_id=mailbox.workspace_id,
        email_address=mailbox.email_address,
        last_sync_cursor=mailbox.last_sync_cursor,
        daily_send_cap=mailbox.daily_send_cap,
        created_at=mailbox.created_at,
    )
