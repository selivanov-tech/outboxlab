from typing import Protocol
from uuid import UUID

from app.contexts.identity.domain.workspace import Workspace


class WorkspaceRepositoryPort(Protocol):
    async def get(self, id: UUID) -> Workspace | None: ...
