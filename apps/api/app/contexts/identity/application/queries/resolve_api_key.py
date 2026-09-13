from uuid import UUID

from app.contexts.identity.application.ports.api_key_repository import (
    ApiKeyRepositoryPort,
)
from app.contexts.identity.domain.api_key import ApiKeyToken


class ResolveApiKeyHandler:
    def __init__(self, keys: ApiKeyRepositoryPort) -> None:
        self._keys = keys

    async def execute(self, raw_key: str) -> UUID | None:
        token = ApiKeyToken.parse(raw_key)
        if token is None:
            return None
        key = await self._keys.get_by_prefix(token.prefix)
        if key is None or not key.accepts(token):
            return None
        return key.workspace_id
