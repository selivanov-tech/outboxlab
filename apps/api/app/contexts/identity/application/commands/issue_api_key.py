from uuid import UUID

from app.contexts.identity.application.ports.api_key_repository import (
    ApiKeyRepositoryPort,
)
from app.contexts.identity.application.ports.workspace_repository import (
    WorkspaceRepositoryPort,
)
from app.contexts.identity.application.queries.get_my_workspace import (
    WorkspaceNotFoundError,
)
from app.contexts.identity.domain.api_key import ApiKey, ApiKeyToken


class IssueApiKeyHandler:
    def __init__(
        self, workspaces: WorkspaceRepositoryPort, keys: ApiKeyRepositoryPort
    ) -> None:
        self._workspaces = workspaces
        self._keys = keys

    async def execute(self, workspace_id: UUID) -> ApiKeyToken:
        if await self._workspaces.get(workspace_id) is None:
            raise WorkspaceNotFoundError
        key, token = ApiKey.issue(workspace_id)
        await self._keys.add(key)
        return token
