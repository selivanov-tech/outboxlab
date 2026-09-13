import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now

MAX_SEND_ATTEMPTS = 3
RETRY_BACKOFF = timedelta(seconds=60)


class SendJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SendJobPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_version: Literal[1] = 1
    campaign_id: UUID
    lead_id: UUID
    step_id: UUID
    step_position: int
    to_email: str
    subject: str
    body: str


class SendJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    mailbox_id: UUID
    lead_id: UUID
    step_id: UUID
    payload: SendJobPayload
    scheduled_at: datetime
    status: SendJobStatus
    attempts: int
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        workspace_id: UUID,
        mailbox_id: UUID,
        payload: SendJobPayload,
        scheduled_at: datetime,
    ) -> "SendJob":
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            lead_id=payload.lead_id,
            step_id=payload.step_id,
            payload=payload,
            scheduled_at=scheduled_at,
            status=SendJobStatus.PENDING,
            attempts=0,
            created_at=now(),
        )


def next_retry_at(attempts: int, moment: datetime) -> datetime | None:
    if attempts >= MAX_SEND_ATTEMPTS:
        return None
    return moment + RETRY_BACKOFF * attempts
