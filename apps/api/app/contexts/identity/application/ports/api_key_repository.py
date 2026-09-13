from typing import Protocol

from app.contexts.identity.domain.api_key import ApiKey


class ApiKeyRepositoryPort(Protocol):
    async def add(self, key: ApiKey) -> None: ...

    async def get_by_prefix(self, prefix: str) -> ApiKey | None: ...
