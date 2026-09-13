from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.messaging.domain.suppression import Suppression
from app.contexts.messaging.infrastructure.db.models import (
    Suppression as SuppressionRow,
)


class SuppressionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, suppression: Suppression) -> None:
        await self._session.execute(
            insert(SuppressionRow)
            .values(
                id=suppression.id,
                workspace_id=suppression.workspace_id,
                email=suppression.email,
                reason=suppression.reason.value,
                source_inbound_id=suppression.source_inbound_id,
                created_at=suppression.created_at,
            )
            .on_conflict_do_nothing(index_elements=["workspace_id", "email", "reason"])
        )

    async def is_suppressed(self, workspace_id: UUID, email: str) -> bool:
        stmt = (
            select(SuppressionRow.id)
            .where(
                SuppressionRow.workspace_id == workspace_id,
                SuppressionRow.email == email.strip().lower(),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def count_addresses(self, workspace_id: UUID) -> int:
        stmt = select(func.count(func.distinct(SuppressionRow.email))).where(
            SuppressionRow.workspace_id == workspace_id
        )
        return int((await self._session.execute(stmt)).scalar_one())
