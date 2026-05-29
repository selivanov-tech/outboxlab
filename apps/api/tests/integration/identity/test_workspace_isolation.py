from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.campaign.infrastructure.db.models import Campaign
from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.persistence.workspace_repo import WorkspaceRepository


async def _set_workspace(session: AsyncSession, ws_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.workspace_id', :id, true)"),
        {"id": ws_id},
    )


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
    session.add(Campaign(workspace_id=ws_a.id, name="a-campaign"))
    await session.flush()

    await _set_workspace(session, str(ws_b.id))
    session.add(Campaign(workspace_id=ws_b.id, name="b-campaign"))
    await session.flush()

    await _set_workspace(session, str(ws_a.id))
    visible = (
        (await session.execute(text("SELECT name FROM campaigns ORDER BY name")))
        .scalars()
        .all()
    )
    assert visible == ["a-campaign"]

    await _set_workspace(session, str(ws_b.id))
    visible = (
        (await session.execute(text("SELECT name FROM campaigns ORDER BY name")))
        .scalars()
        .all()
    )
    assert visible == ["b-campaign"]
