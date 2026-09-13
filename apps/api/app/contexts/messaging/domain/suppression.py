import uuid
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now


class SuppressionReason(StrEnum):
    UNSUBSCRIBE = "unsubscribe"
    HARD_BOUNCE = "hard_bounce"


class Suppression(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    email: str
    reason: SuppressionReason
    source_inbound_id: UUID | None
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        workspace_id: UUID,
        email: str,
        reason: SuppressionReason,
        source_inbound_id: UUID | None,
    ) -> "Suppression":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            email=email.strip().lower(),
            reason=reason,
            source_inbound_id=source_inbound_id,
            created_at=now(),
        )
