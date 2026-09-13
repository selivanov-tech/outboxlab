import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.infrastructure.db.models import Campaign as CampaignRow
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.contexts.mailbox.infrastructure.db.models import Mailbox as MailboxRow
from app.shared.util.clock import now


async def _set_workspace(session: AsyncSession, ws_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.workspace_id', :id, true)"),
        {"id": ws_id},
    )


async def _add_campaign(
    session: AsyncSession, workspace_id: uuid.UUID, name: str
) -> None:
    mailbox_id = uuid.uuid7()
    session.add(
        MailboxRow(
            id=mailbox_id,
            workspace_id=workspace_id,
            email_address=f"{name}@example.com",
            last_sync_cursor=None,
            created_at=now(),
        )
    )
    await session.flush()
    session.add(
        CampaignRow(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            name=name,
            status="draft",
            created_at=now(),
        )
    )
    await session.flush()


async def test_workspace_isolation_on_campaigns(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    ws_a = Workspace.new("tenant-a")
    await repo.add(ws_a)
    ws_b = Workspace.new("tenant-b")
    await repo.add(ws_b)

    # Superuser bypasses RLS even with FORCE; switch to outboxlab_app
    # (NOLOGIN, non-superuser) so the policy actually applies.
    await session.execute(text("SET LOCAL ROLE outboxlab_app"))

    await _set_workspace(session, str(ws_a.id))
    await _add_campaign(session, ws_a.id, "a-campaign")

    await _set_workspace(session, str(ws_b.id))
    await _add_campaign(session, ws_b.id, "b-campaign")

    await _set_workspace(session, str(ws_a.id))
    visible = (
        (
            await session.execute(
                text("SELECT name FROM campaign__campaigns ORDER BY name")
            )
        )
        .scalars()
        .all()
    )
    assert visible == ["a-campaign"]

    await _set_workspace(session, str(ws_b.id))
    visible = (
        (
            await session.execute(
                text("SELECT name FROM campaign__campaigns ORDER BY name")
            )
        )
        .scalars()
        .all()
    )
    assert visible == ["b-campaign"]
