from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.infrastructure.persistence.mailbox_repo import (
    MailboxRepository,
)


async def _seed_workspace(session: AsyncSession) -> Workspace:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)
    return ws


async def test_add_and_get_by_workspace_roundtrip(session: AsyncSession) -> None:
    ws = await _seed_workspace(session)
    repo = MailboxRepository(session)
    mailbox = Mailbox.new(ws.id, "ops@example.com")
    await repo.add(mailbox)

    fetched = await repo.get_by_workspace(ws.id)

    assert fetched == mailbox


async def test_update_cursor_persists(session: AsyncSession) -> None:
    ws = await _seed_workspace(session)
    repo = MailboxRepository(session)
    mailbox = Mailbox.new(ws.id, "ops@example.com")
    await repo.add(mailbox)

    await repo.update_cursor(mailbox.with_cursor("999"))

    fetched = await repo.get_by_workspace(ws.id)
    assert fetched is not None
    assert fetched.last_sync_cursor == "999"


async def test_get_by_workspace_returns_none_when_absent(session: AsyncSession) -> None:
    ws = await _seed_workspace(session)
    assert await MailboxRepository(session).get_by_workspace(ws.id) is None
