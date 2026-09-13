from collections.abc import Iterable
from datetime import datetime

from app.contexts.campaign.application.ports.send_job_repository import (
    ClaimedSendJob,
)
from app.contexts.campaign.application.process_send_jobs import SendJobOutcome
from app.contexts.campaign.domain.lead import Lead, LeadState
from app.shared.infrastructure.metrics import (
    record_email_sent,
    record_lead_paused,
    record_send_failure,
)

_FAILURE_REASONS = {
    SendJobOutcome.RETRYING: "retrying",
    SendJobOutcome.FAILED: "failed",
    SendJobOutcome.SUPPRESSED: "suppressed",
}


def record_send_job_outcome(
    job: ClaimedSendJob, outcome: SendJobOutcome, moment: datetime
) -> None:
    if outcome is SendJobOutcome.SENT:
        record_email_sent((moment - job.scheduled_at).total_seconds())
    elif outcome in _FAILURE_REASONS:
        record_send_failure(_FAILURE_REASONS[outcome])


def record_stopped_leads(leads: Iterable[Lead]) -> None:
    for lead in leads:
        if lead.state is LeadState.PAUSED and lead.stop_reason is not None:
            record_lead_paused(lead.stop_reason.value)
