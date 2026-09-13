from typing import Protocol
from uuid import UUID

from app.contexts.messaging.domain.suppression import Suppression


class SuppressionRepositoryPort(Protocol):
    async def add(self, suppression: Suppression) -> None: ...

    async def is_suppressed(self, workspace_id: UUID, email: str) -> bool: ...
