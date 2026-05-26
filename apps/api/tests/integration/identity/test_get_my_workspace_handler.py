import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.application.queries.get_my_workspace import (
    GetMyWorkspaceHandler,
    WorkspaceNotFoundError,
)
from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.persistence.workspace_repo import WorkspaceRepository


async def test_returns_workspace_when_present(session: AsyncSession) -> None:
    repo = WorkspaceRepository(session)
    ws = Workspace.new("acme")
    await repo.add(ws)
    handler = GetMyWorkspaceHandler(repo)

    result = await handler.execute(ws.id)

    assert result == ws


async def test_raises_when_workspace_missing(session: AsyncSession) -> None:
    handler = GetMyWorkspaceHandler(WorkspaceRepository(session))

    with pytest.raises(WorkspaceNotFoundError):
        await handler.execute(uuid.uuid7())
