from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.contexts.campaign.domain.send_job import SendJob, SendJobPayload


@dataclass(frozen=True)
class ClaimedSendJob:
    id: UUID
    workspace_id: UUID
    mailbox_id: UUID
    lead_id: UUID
    payload: SendJobPayload
    attempts: int
    scheduled_at: datetime


class SendJobRepositoryPort(Protocol):
    async def add_many(self, jobs: Sequence[SendJob]) -> None: ...

    async def claim(
        self,
        *,
        workspace_id: UUID,
        worker_id: str,
        limit: int,
        moment: datetime,
        lease: timedelta,
    ) -> list[ClaimedSendJob]: ...

    async def complete(
        self, job_id: UUID, outbound_message_id: UUID, moment: datetime
    ) -> None: ...

    async def release(
        self, job_id: UUID, retry_at: datetime, reason: str, moment: datetime
    ) -> None: ...

    async def retry_later(
        self, job_id: UUID, retry_at: datetime, error: str, moment: datetime
    ) -> None: ...

    async def fail(self, job_id: UUID, error: str, moment: datetime) -> None: ...

    async def cancel(self, job_id: UUID, moment: datetime) -> None: ...
