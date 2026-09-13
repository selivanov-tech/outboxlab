from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.messaging.infrastructure.persistence.outbound_repo import (
    OutboundMessageRepository,
)
from app.contexts.messaging.infrastructure.persistence.suppression_repo import (
    SuppressionRepository,
)


class MessagingMailboxActivity:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sent_since(self, mailbox_id: UUID, since: datetime) -> int:
        return await OutboundMessageRepository(self._session).count_sent_since(
            mailbox_id, since
        )

    async def suppressed_addresses(self, workspace_id: UUID) -> int:
        return await SuppressionRepository(self._session).count_addresses(workspace_id)
