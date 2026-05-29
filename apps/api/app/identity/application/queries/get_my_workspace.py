from uuid import UUID

from app.identity.application.ports.workspace_repository import WorkspaceRepositoryPort
from app.identity.domain.workspace import Workspace


class WorkspaceNotFoundError(Exception):
    pass


class GetMyWorkspaceHandler:
    def __init__(self, repo: WorkspaceRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, workspace_id: UUID) -> Workspace:
        workspace = await self._repo.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        return workspace
