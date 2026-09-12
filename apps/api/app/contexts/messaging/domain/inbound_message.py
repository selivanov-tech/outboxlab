import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.contexts.messaging.domain.intent import Intent
from app.shared.util.clock import now


class InboundMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    mailbox_id: UUID
    provider_message_id: str
    provider_thread_id: str
    from_email: str
    subject: str
    snippet: str
    in_reply_to_header: str | None
    references_header: str | None
    matched_outbound_id: UUID | None
    intent: Intent | None
    received_at: datetime
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        workspace_id: UUID,
        mailbox_id: UUID,
        provider_message_id: str,
        provider_thread_id: str,
        from_email: str,
        subject: str,
        snippet: str,
        in_reply_to_header: str | None,
        references_header: str | None,
        received_at: datetime,
    ) -> "InboundMessage":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            provider_message_id=provider_message_id,
            provider_thread_id=provider_thread_id,
            from_email=from_email,
            subject=subject,
            snippet=snippet,
            in_reply_to_header=in_reply_to_header,
            references_header=references_header,
            matched_outbound_id=None,
            intent=None,
            received_at=received_at,
            created_at=now(),
        )

    def matched_to(self, outbound_id: UUID) -> "InboundMessage":
        return self.model_copy(update={"matched_outbound_id": outbound_id})

    def classified_as(self, intent: Intent) -> "InboundMessage":
        return self.model_copy(update={"intent": intent})
