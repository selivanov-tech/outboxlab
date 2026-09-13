from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.domain.api_key import ApiKey
from app.contexts.identity.infrastructure.db.models import ApiKey as ApiKeyRow


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, key: ApiKey) -> None:
        self._session.add(
            ApiKeyRow(
                id=key.id,
                workspace_id=key.workspace_id,
                prefix=key.prefix,
                secret_hash=key.secret_hash,
                created_at=key.created_at,
                revoked_at=key.revoked_at,
            )
        )
        await self._session.flush()

    async def get_by_prefix(self, prefix: str) -> ApiKey | None:
        stmt = select(ApiKeyRow).where(ApiKeyRow.prefix == prefix)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return ApiKey(
            id=row.id,
            workspace_id=row.workspace_id,
            prefix=row.prefix,
            secret_hash=row.secret_hash,
            created_at=row.created_at,
            revoked_at=row.revoked_at,
        )
