import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.persistence.workspace_repo import WorkspaceRepository


async def test_add_and_fetch_roundtrip(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    ws = Workspace.new("acme-corp")
    await repo.add(ws)

    fetched = await repo.get(ws.id)

    assert fetched == ws


async def test_list_orders_by_created_at(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    a = Workspace.new("alpha")
    await repo.add(a)
    b = Workspace.new("beta")
    await repo.add(b)
    listed = await repo.list()
    ids = [ws.id for ws in listed]
    assert ids.index(a.id) < ids.index(b.id)


async def test_get_missing_returns_none(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    assert await repo.get(uuid.uuid7()) is None
