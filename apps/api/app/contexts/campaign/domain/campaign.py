import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.contexts.campaign.domain.errors import (
    CampaignHasNoStepsError,
    CampaignNotActiveError,
    LeadNotInCampaignError,
    LeadTransitionError,
    NegativeStepDelayError,
)
from app.contexts.campaign.domain.lead import (
    Lead,
    LeadState,
    StopReason,
    normalize_email,
)
from app.contexts.campaign.domain.send_job import SendJob, SendJobPayload
from app.shared.util.clock import now

BOUNCE_INTENT = "bounce"
UNSUBSCRIBE_INTENT = "unsubscribe"

_SENDABLE_STATES = frozenset({LeadState.SCHEDULED, LeadState.SENT})
_REPLYABLE_STATES = frozenset({LeadState.SENT, LeadState.DONE})


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"


class StepDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    body: str
    delay_seconds: int


class Step(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    position: int
    subject: str
    body: str
    delay_seconds: int


class Campaign(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    mailbox_id: UUID
    name: str
    status: CampaignStatus
    steps: tuple[Step, ...]
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        workspace_id: UUID,
        mailbox_id: UUID,
        name: str,
        steps: Sequence[StepDraft],
    ) -> "Campaign":
        if not steps:
            raise CampaignHasNoStepsError
        if any(step.delay_seconds < 0 for step in steps):
            raise NegativeStepDelayError
        return cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            name=name,
            status=CampaignStatus.DRAFT,
            steps=tuple(
                Step(
                    id=uuid.uuid7(),
                    position=position,
                    subject=draft.subject,
                    body=draft.body,
                    delay_seconds=draft.delay_seconds,
                )
                for position, draft in enumerate(steps, start=1)
            ),
            created_at=now(),
        )

    @property
    def is_active(self) -> bool:
        return self.status is CampaignStatus.ACTIVE

    def add_leads(
        self, emails: Iterable[str], known_emails: Iterable[str]
    ) -> list[Lead]:
        seen = {normalize_email(email) for email in known_emails}
        leads: list[Lead] = []
        for raw in emails:
            email = normalize_email(raw)
            if not email or email in seen:
                continue
            seen.add(email)
            leads.append(
                Lead.new(
                    workspace_id=self.workspace_id, campaign_id=self.id, email=email
                )
            )
        return leads

    def start(
        self, pending_leads: Sequence[Lead], moment: datetime
    ) -> tuple["Campaign", list[Lead], list[SendJob]]:
        if self.is_active:
            return self, [], []
        started = self.model_copy(update={"status": CampaignStatus.ACTIVE})
        scheduled, jobs = started.schedule(pending_leads, moment)
        return started, scheduled, jobs

    def schedule(
        self, leads: Sequence[Lead], moment: datetime
    ) -> tuple[list[Lead], list[SendJob]]:
        if not self.is_active:
            raise CampaignNotActiveError
        first_step = self.steps[0]
        scheduled: list[Lead] = []
        jobs: list[SendJob] = []
        for lead in leads:
            self._ensure_member(lead)
            if lead.state is not LeadState.PENDING:
                raise LeadTransitionError(lead.state, "be scheduled")
            scheduled.append(_moved(lead, LeadState.SCHEDULED, moment))
            jobs.append(self._job(lead, first_step, moment))
        return scheduled, jobs

    def accepts_send(self, lead: Lead, step_position: int) -> bool:
        return (
            self.is_active
            and lead.campaign_id == self.id
            and lead.state in _SENDABLE_STATES
            and lead.steps_sent == step_position - 1
        )

    def record_sent(
        self, lead: Lead, step_position: int, sent_at: datetime
    ) -> tuple[Lead, SendJob | None]:
        self._ensure_member(lead)
        if not self.accepts_send(lead, step_position):
            raise LeadTransitionError(lead.state, f"record step {step_position} sent")
        if step_position == len(self.steps):
            return (
                _moved(lead, LeadState.DONE, sent_at, steps_sent=step_position),
                None,
            )
        next_step = self.steps[step_position]
        return (
            _moved(lead, LeadState.SENT, sent_at, steps_sent=step_position),
            self._job(lead, next_step, sent_at),
        )

    def stop_on_reply(self, lead: Lead, intent: str, moment: datetime) -> Lead:
        self._ensure_member(lead)
        if lead.is_stopped:
            return lead
        if lead.state not in _REPLYABLE_STATES:
            raise LeadTransitionError(lead.state, "stop on a reply")
        if intent == BOUNCE_INTENT:
            return _moved(
                lead,
                LeadState.FAILED,
                moment,
                stop_reason=StopReason.BOUNCED,
                reply_intent=intent,
            )
        reason = (
            StopReason.UNSUBSCRIBED
            if intent == UNSUBSCRIBE_INTENT
            else StopReason.REPLIED
        )
        return _moved(
            lead, LeadState.PAUSED, moment, stop_reason=reason, reply_intent=intent
        )

    def fail_lead(self, lead: Lead, reason: StopReason, moment: datetime) -> Lead:
        self._ensure_member(lead)
        if lead.is_stopped:
            return lead
        if lead.state not in _SENDABLE_STATES:
            raise LeadTransitionError(lead.state, "fail")
        return _moved(lead, LeadState.FAILED, moment, stop_reason=reason)

    def _ensure_member(self, lead: Lead) -> None:
        if lead.campaign_id != self.id:
            raise LeadNotInCampaignError

    def _job(self, lead: Lead, step: Step, after: datetime) -> SendJob:
        return SendJob.new(
            workspace_id=self.workspace_id,
            mailbox_id=self.mailbox_id,
            payload=SendJobPayload(
                campaign_id=self.id,
                lead_id=lead.id,
                step_id=step.id,
                step_position=step.position,
                to_email=lead.email,
                subject=step.subject,
                body=step.body,
            ),
            scheduled_at=after + timedelta(seconds=step.delay_seconds),
        )


def _moved(lead: Lead, state: LeadState, moment: datetime, **changes: object) -> Lead:
    return lead.model_copy(update={"state": state, "updated_at": moment, **changes})
