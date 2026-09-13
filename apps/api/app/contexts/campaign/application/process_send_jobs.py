from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.contexts.campaign.application.ports.campaign_repository import (
    CampaignRepositoryPort,
)
from app.contexts.campaign.application.ports.email_dispatch import (
    DispatchDeferred,
    DispatchFailed,
    DispatchSent,
    DispatchSuppressed,
    EmailDispatchPort,
)
from app.contexts.campaign.application.ports.lead_repository import LeadRepositoryPort
from app.contexts.campaign.application.ports.send_job_repository import (
    ClaimedSendJob,
    SendJobRepositoryPort,
)
from app.contexts.campaign.domain.lead import StopReason
from app.contexts.campaign.domain.send_job import CLAIM_LEASE, next_retry_at


class SendJobOutcome(StrEnum):
    SENT = "sent"
    DEFERRED = "deferred"
    SUPPRESSED = "suppressed"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SendJobNotClaimedError(Exception):
    pass


@dataclass(frozen=True)
class ProcessedSendJob:
    job: ClaimedSendJob
    outcome: SendJobOutcome


class ClaimDueSendJobsHandler:
    def __init__(self, jobs: SendJobRepositoryPort) -> None:
        self._jobs = jobs

    async def execute(
        self, *, workspace_id: UUID, worker_id: str, limit: int, moment: datetime
    ) -> list[ClaimedSendJob]:
        return await self._jobs.claim(
            workspace_id=workspace_id,
            worker_id=worker_id,
            limit=limit,
            moment=moment,
            lease=CLAIM_LEASE,
        )


class ProcessClaimedSendJobHandler:
    def __init__(
        self,
        campaigns: CampaignRepositoryPort,
        leads: LeadRepositoryPort,
        jobs: SendJobRepositoryPort,
        dispatch: EmailDispatchPort,
    ) -> None:
        self._campaigns = campaigns
        self._leads = leads
        self._jobs = jobs
        self._dispatch = dispatch

    async def execute(self, job: ClaimedSendJob, moment: datetime) -> SendJobOutcome:
        step_position = job.payload.step_position
        campaign = await self._campaigns.get(job.payload.campaign_id)
        lead = await self._leads.get(job.lead_id)
        if (
            campaign is None
            or lead is None
            or not campaign.accepts_send(lead, step_position)
        ):
            await self._jobs.cancel(job.id, moment)
            return SendJobOutcome.CANCELLED

        result = await self._dispatch.dispatch(
            workspace_id=job.workspace_id,
            to_email=job.payload.to_email,
            subject=job.payload.subject,
            body=job.payload.body,
        )
        match result:
            case DispatchSent(outbound_message_id=outbound_message_id, sent_at=sent_at):
                advanced, next_job = campaign.record_sent(lead, step_position, sent_at)
                await self._leads.update_many([advanced])
                await self._jobs.complete(job.id, outbound_message_id, moment)
                if next_job is not None:
                    await self._jobs.add_many([next_job])
                return SendJobOutcome.SENT
            case DispatchDeferred(retry_at=retry_at, reason=reason):
                await self._jobs.release(job.id, retry_at, reason, moment)
                return SendJobOutcome.DEFERRED
            case DispatchSuppressed():
                await self._leads.update_many(
                    [campaign.fail_lead(lead, StopReason.SUPPRESSED, moment)]
                )
                await self._jobs.cancel(job.id, moment)
                return SendJobOutcome.SUPPRESSED
            case DispatchFailed(error=error):
                retry_at = next_retry_at(job.attempts, moment)
                if retry_at is not None:
                    await self._jobs.retry_later(job.id, retry_at, error, moment)
                    return SendJobOutcome.RETRYING
                await self._leads.update_many(
                    [campaign.fail_lead(lead, StopReason.SEND_FAILED, moment)]
                )
                await self._jobs.fail(job.id, error, moment)
                return SendJobOutcome.FAILED


class ProcessSendJobByIdHandler:
    def __init__(
        self, jobs: SendJobRepositoryPort, process: ProcessClaimedSendJobHandler
    ) -> None:
        self._jobs = jobs
        self._process = process

    async def execute(
        self, *, job_id: UUID, workspace_id: UUID, moment: datetime
    ) -> ProcessedSendJob:
        job = await self._jobs.get_claimed(job_id, workspace_id)
        if job is None:
            raise SendJobNotClaimedError
        return ProcessedSendJob(
            job=job, outcome=await self._process.execute(job, moment)
        )
