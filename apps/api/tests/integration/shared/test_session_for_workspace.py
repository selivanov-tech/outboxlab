import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.infrastructure.db.models import Mailbox as MailboxRow
from app.shared.util.clock import now


async def test_session_for_workspace_sets_guc(session: AsyncSession) -> None:
    ws = Workspace.new("acme")
    await WorkspaceRepository(session).add(ws)

    # The shared `session` fixture is superuser, which bypasses RLS even with
    # FORCE. Switch to outboxlab_app so the GUC set by the helper actually
    # gates the insert/read — mirroring the worker/seed runtime role.
    await session.execute(text("SET LOCAL ROLE outboxlab_app"))
    await session.execute(
        text("SELECT set_config('app.workspace_id', :ws, true)"),
        {"ws": str(ws.id)},
    )

    mailbox_id = uuid.uuid7()
    session.add(
        MailboxRow(
            id=mailbox_id,
            workspace_id=ws.id,
            email_address="ops@example.com",
            last_sync_cursor=None,
            created_at=now(),
        )
    )
    await session.flush()

    visible = (
        (await session.execute(text("SELECT id FROM mailbox__mailboxes")))
        .scalars()
        .all()
    )
    assert list(visible) == [mailbox_id]
