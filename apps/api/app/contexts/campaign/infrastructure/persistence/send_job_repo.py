from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import DateTime, Integer, func, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.application.ports.send_job_repository import (
    ClaimedSendJob,
)
from app.contexts.campaign.domain.send_job import (
    SendJob,
    SendJobPayload,
    SendJobStatus,
)
from app.contexts.campaign.infrastructure.db.models import Lead as LeadRow
from app.contexts.campaign.infrastructure.db.models import SendJob as SendJobRow

CLAIM_SQL = text(
    """
    UPDATE campaign__send_jobs
    SET status = 'running',
        locked_at = :moment,
        locked_by = :worker_id,
        attempts = attempts + 1,
        updated_at = :moment
    WHERE id IN (
        SELECT id FROM campaign__send_jobs
        WHERE workspace_id = :workspace_id
          AND (
            (status = 'pending' AND scheduled_at <= :moment)
            OR (status = 'running' AND locked_at < :lease_expired_before)
          )
        ORDER BY scheduled_at
        LIMIT :limit
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id, workspace_id, mailbox_id, lead_id, payload, attempts, scheduled_at
    """
).columns(
    id=PgUUID(as_uuid=True),
    workspace_id=PgUUID(as_uuid=True),
    mailbox_id=PgUUID(as_uuid=True),
    lead_id=PgUUID(as_uuid=True),
    payload=JSONB(),
    attempts=Integer(),
    scheduled_at=DateTime(timezone=True),
)


class SendJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, jobs: Sequence[SendJob]) -> None:
        self._session.add_all(
            SendJobRow(
                id=job.id,
                workspace_id=job.workspace_id,
                mailbox_id=job.mailbox_id,
                lead_id=job.lead_id,
                step_id=job.step_id,
                payload=job.payload.model_dump(mode="json"),
                scheduled_at=job.scheduled_at,
                status=job.status.value,
                attempts=job.attempts,
                locked_at=None,
                locked_by=None,
                last_error=None,
                outbound_message_id=None,
                created_at=job.created_at,
                updated_at=job.created_at,
            )
            for job in jobs
        )
        await self._session.flush()

    async def claim(
        self,
        *,
        workspace_id: UUID,
        worker_id: str,
        limit: int,
        moment: datetime,
        lease: timedelta,
    ) -> list[ClaimedSendJob]:
        rows = (
            await self._session.execute(
                CLAIM_SQL,
                {
                    "workspace_id": workspace_id,
                    "worker_id": worker_id,
                    "limit": limit,
                    "moment": moment,
                    "lease_expired_before": moment - lease,
                },
            )
        ).all()
        claimed = [
            ClaimedSendJob(
                id=row.id,
                workspace_id=row.workspace_id,
                mailbox_id=row.mailbox_id,
                lead_id=row.lead_id,
                payload=SendJobPayload.model_validate(row.payload),
                attempts=row.attempts,
                scheduled_at=row.scheduled_at,
            )
            for row in rows
        ]
        return sorted(claimed, key=lambda job: job.scheduled_at)

    async def complete(
        self, job_id: UUID, outbound_message_id: UUID, moment: datetime
    ) -> None:
        await self._set(
            job_id,
            moment,
            status=SendJobStatus.DONE.value,
            outbound_message_id=outbound_message_id,
            last_error=None,
        )

    async def release(
        self, job_id: UUID, retry_at: datetime, reason: str, moment: datetime
    ) -> None:
        await self._reschedule(
            job_id,
            retry_at,
            moment,
            last_error=reason,
            attempts=SendJobRow.attempts - 1,
        )

    async def retry_later(
        self, job_id: UUID, retry_at: datetime, error: str, moment: datetime
    ) -> None:
        await self._reschedule(job_id, retry_at, moment, last_error=error)

    async def fail(self, job_id: UUID, error: str, moment: datetime) -> None:
        await self._set(
            job_id, moment, status=SendJobStatus.FAILED.value, last_error=error
        )

    async def cancel(self, job_id: UUID, moment: datetime) -> None:
        await self._set(job_id, moment, status=SendJobStatus.CANCELLED.value)

    async def cancel_pending_for_lead(self, lead_id: UUID, moment: datetime) -> None:
        await self._session.execute(
            update(SendJobRow)
            .where(
                SendJobRow.lead_id == lead_id,
                SendJobRow.status == SendJobStatus.PENDING.value,
            )
            .values(status=SendJobStatus.CANCELLED.value, updated_at=moment)
        )

    async def find_lead_id_by_outbound_message(
        self, outbound_message_id: UUID
    ) -> UUID | None:
        stmt = (
            select(SendJobRow.lead_id)
            .where(SendJobRow.outbound_message_id == outbound_message_id)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_send_at_by_lead(self, campaign_id: UUID) -> dict[UUID, datetime]:
        stmt = (
            select(SendJobRow.lead_id, func.min(SendJobRow.scheduled_at))
            .join(LeadRow, LeadRow.id == SendJobRow.lead_id)
            .where(
                LeadRow.campaign_id == campaign_id,
                SendJobRow.status.in_(
                    [SendJobStatus.PENDING.value, SendJobStatus.RUNNING.value]
                ),
            )
            .group_by(SendJobRow.lead_id)
        )
        return {
            lead_id: scheduled_at
            for lead_id, scheduled_at in (await self._session.execute(stmt)).all()
        }

    async def _reschedule(
        self,
        job_id: UUID,
        retry_at: datetime,
        moment: datetime,
        **values: object,
    ) -> None:
        await self._set(
            job_id,
            moment,
            status=SendJobStatus.PENDING.value,
            scheduled_at=retry_at,
            locked_at=None,
            locked_by=None,
            **values,
        )

    async def _set(self, job_id: UUID, moment: datetime, **values: object) -> None:
        await self._session.execute(
            update(SendJobRow)
            .where(SendJobRow.id == job_id)
            .values(updated_at=moment, **values)
        )
