from uuid import UUID

from app.contexts.identity.application.queries.resolve_api_key import (
    ResolveApiKeyHandler,
)
from app.contexts.identity.infrastructure.persistence.api_key_repo import (
    ApiKeyRepository,
)
from app.shared.infrastructure.db.engine import get_session_factory


async def resolve_workspace_by_api_key(raw_key: str) -> UUID | None:
    async with get_session_factory()() as session:
        return await ResolveApiKeyHandler(ApiKeyRepository(session)).execute(raw_key)
