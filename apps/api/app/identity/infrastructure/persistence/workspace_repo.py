from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.db.models import Workspace as WorkspaceRow


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: UUID) -> Workspace | None:
        row = await self._session.get(WorkspaceRow, id)
        return _to_domain(row) if row is not None else None

    async def list(self) -> list[Workspace]:
        stmt = select(WorkspaceRow).order_by(WorkspaceRow.created_at)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def add(self, workspace: Workspace) -> None:
        self._session.add(_to_row(workspace))
        await self._session.flush()


def _to_domain(row: WorkspaceRow) -> Workspace:
    return Workspace(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
    )


def _to_row(workspace: Workspace) -> WorkspaceRow:
    return WorkspaceRow(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )
