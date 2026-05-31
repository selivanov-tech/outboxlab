import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.infrastructure.db.models import Mailbox as MailboxRow
from app.contexts.messaging.infrastructure.db.models import (
    OutboundMessage as OutboundMessageRow,
)
from app.shared.util.clock import now


async def _set_workspace(session: AsyncSession, ws_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.workspace_id', :id, true)"),
        {"id": ws_id},
    )


async def test_outbound_messages_isolation(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    ws_a = Workspace.new("tenant-a")
    await repo.add(ws_a)
    ws_b = Workspace.new("tenant-b")
    await repo.add(ws_b)

    # Superuser bypasses RLS even with FORCE; switch to outboxlab_app
    # (NOLOGIN, non-superuser) so the policy actually applies — this also
    # exercises that mailboxes is reachable once the GUC is set.
    await session.execute(text("SET LOCAL ROLE outboxlab_app"))

    mb_a_id = uuid.uuid7()
    mb_b_id = uuid.uuid7()

    await _set_workspace(session, str(ws_a.id))
    session.add(
        MailboxRow(
            id=mb_a_id,
            workspace_id=ws_a.id,
            email_address="a@example.com",
            last_sync_cursor=None,
            created_at=now(),
        )
    )
    session.add(
        OutboundMessageRow(
            id=uuid.uuid7(),
            workspace_id=ws_a.id,
            mailbox_id=mb_a_id,
            to_email="lead@example.com",
            subject="s",
            body="b",
            rfc822_message_id="<a@example.com>",
            provider_message_id=None,
            provider_thread_id=None,
            created_at=now(),
        )
    )
    await session.flush()

    await _set_workspace(session, str(ws_b.id))
    session.add(
        MailboxRow(
            id=mb_b_id,
            workspace_id=ws_b.id,
            email_address="b@example.com",
            last_sync_cursor=None,
            created_at=now(),
        )
    )
    session.add(
        OutboundMessageRow(
            id=uuid.uuid7(),
            workspace_id=ws_b.id,
            mailbox_id=mb_b_id,
            to_email="lead@example.com",
            subject="s",
            body="b",
            rfc822_message_id="<b@example.com>",
            provider_message_id=None,
            provider_thread_id=None,
            created_at=now(),
        )
    )
    await session.flush()

    await _set_workspace(session, str(ws_a.id))
    visible = (
        (
            await session.execute(
                text(
                    "SELECT rfc822_message_id FROM messaging__outbound_messages "
                    "ORDER BY 1"
                )
            )
        )
        .scalars()
        .all()
    )
    assert visible == ["<a@example.com>"]

    await _set_workspace(session, str(ws_b.id))
    visible = (
        (
            await session.execute(
                text(
                    "SELECT rfc822_message_id FROM messaging__outbound_messages "
                    "ORDER BY 1"
                )
            )
        )
        .scalars()
        .all()
    )
    assert visible == ["<b@example.com>"]
