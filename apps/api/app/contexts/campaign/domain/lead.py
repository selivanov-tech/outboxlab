import uuid
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now


class LeadState(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class StopReason(StrEnum):
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    SUPPRESSED = "suppressed"
    SEND_FAILED = "send_failed"


class Lead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    campaign_id: UUID
    email: str
    state: LeadState
    steps_sent: int
    stop_reason: StopReason | None
    reply_intent: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, *, workspace_id: UUID, campaign_id: UUID, email: str) -> "Lead":
        created_at = now()
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            email=normalize_email(email),
            state=LeadState.PENDING,
            steps_sent=0,
            stop_reason=None,
            reply_intent=None,
            created_at=created_at,
            updated_at=created_at,
        )

    @property
    def is_stopped(self) -> bool:
        return self.state in (LeadState.PAUSED, LeadState.FAILED)


def normalize_email(email: str) -> str:
    return email.strip().lower()
