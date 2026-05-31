import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now


class OutboundMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    mailbox_id: UUID
    to_email: str
    subject: str
    body: str
    rfc822_message_id: str
    provider_message_id: str | None
    provider_thread_id: str | None
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        workspace_id: UUID,
        mailbox_id: UUID,
        to_email: str,
        subject: str,
        body: str,
        rfc822_message_id: str,
    ) -> "OutboundMessage":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            to_email=to_email,
            subject=subject,
            body=body,
            rfc822_message_id=rfc822_message_id,
            provider_message_id=None,
            provider_thread_id=None,
            created_at=now(),
        )

    def sent(
        self, provider_message_id: str, provider_thread_id: str
    ) -> "OutboundMessage":
        return self.model_copy(
            update={
                "provider_message_id": provider_message_id,
                "provider_thread_id": provider_thread_id,
            }
        )
