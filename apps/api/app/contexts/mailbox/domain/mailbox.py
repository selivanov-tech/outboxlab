import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now

DEFAULT_DAILY_SEND_CAP = 20


class Mailbox(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    email_address: str
    last_sync_cursor: str | None
    daily_send_cap: int
    created_at: datetime

    @classmethod
    def new(
        cls,
        workspace_id: UUID,
        email_address: str,
        daily_send_cap: int = DEFAULT_DAILY_SEND_CAP,
    ) -> "Mailbox":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            email_address=email_address.lower(),
            last_sync_cursor=None,
            daily_send_cap=daily_send_cap,
            created_at=now(),
        )

    def with_cursor(self, sync_cursor: str) -> "Mailbox":
        return self.model_copy(update={"last_sync_cursor": sync_cursor})
