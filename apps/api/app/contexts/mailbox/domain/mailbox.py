import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now


class Mailbox(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    email_address: str
    last_sync_cursor: str | None
    created_at: datetime

    @classmethod
    def new(cls, workspace_id: UUID, email_address: str) -> "Mailbox":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            email_address=email_address.lower(),
            last_sync_cursor=None,
            created_at=now(),
        )

    def with_cursor(self, sync_cursor: str) -> "Mailbox":
        return self.model_copy(update={"last_sync_cursor": sync_cursor})
