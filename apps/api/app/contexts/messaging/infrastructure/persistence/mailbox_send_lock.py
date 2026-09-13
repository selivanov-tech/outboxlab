from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TRY_LOCK = text("SELECT pg_try_advisory_xact_lock(hashtext(:mailbox_key))")


class PostgresMailboxSendLock:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_acquire(self, mailbox_id: UUID) -> bool:
        result = await self._session.execute(
            _TRY_LOCK, {"mailbox_key": str(mailbox_id)}
        )
        return bool(result.scalar_one())
