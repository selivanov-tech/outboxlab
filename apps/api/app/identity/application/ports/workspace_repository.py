from typing import Protocol
from uuid import UUID

from app.identity.domain.workspace import Workspace


class WorkspaceRepositoryPort(Protocol):
    async def get(self, id: UUID) -> Workspace | None: ...
