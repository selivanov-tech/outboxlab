import uuid
from datetime import timedelta

from prometheus_client import REGISTRY

from app.contexts.campaign.application.ports.send_job_repository import (
    ClaimedSendJob,
)
from app.contexts.campaign.application.process_send_jobs import SendJobOutcome
from app.contexts.campaign.domain.campaign import Campaign, StepDraft
from app.contexts.campaign.infrastructure.metrics import (
    record_send_job_outcome,
    record_stopped_leads,
)
from app.contexts.campaign.domain.send_job import SendJobPayload
from app.shared.infrastructure.metrics import record_replies_classified
from app.shared.util.clock import now


def _sample(name: str, labels: dict[str, str] | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def _job() -> ClaimedSendJob:
    return ClaimedSendJob(
        id=uuid.uuid7(),
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        lead_id=uuid.uuid7(),
        payload=SendJobPayload(
            campaign_id=uuid.uuid7(),
            lead_id=uuid.uuid7(),
            step_id=uuid.uuid7(),
            step_position=1,
            to_email="lead@example.com",
            subject="Hello",
            body="First touch",
        ),
        attempts=1,
        scheduled_at=now() - timedelta(seconds=42),
    )


def test_a_sent_job_counts_an_email_and_its_queue_latency() -> None:
    sent_before = _sample("emails_sent_total")
    latency_count_before = _sample("send_job_latency_seconds_count")
    latency_sum_before = _sample("send_job_latency_seconds_sum")
    job = _job()

    record_send_job_outcome(
        job, SendJobOutcome.SENT, job.scheduled_at + timedelta(seconds=42)
    )

    assert _sample("emails_sent_total") == sent_before + 1
    assert _sample("send_job_latency_seconds_count") == latency_count_before + 1
    assert _sample("send_job_latency_seconds_sum") == latency_sum_before + 42


def test_failures_are_counted_by_reason_and_deferrals_are_not() -> None:
    reasons = ("retrying", "failed", "suppressed")
    before = {
        reason: _sample("send_failures_total", {"reason": reason}) for reason in reasons
    }
    sent_before = _sample("emails_sent_total")

    for outcome in (
        SendJobOutcome.RETRYING,
        SendJobOutcome.FAILED,
        SendJobOutcome.SUPPRESSED,
        SendJobOutcome.DEFERRED,
        SendJobOutcome.CANCELLED,
    ):
        record_send_job_outcome(_job(), outcome, now())

    for reason in reasons:
        assert _sample("send_failures_total", {"reason": reason}) == before[reason] + 1
    assert _sample("emails_sent_total") == sent_before


def test_only_paused_leads_count_as_paused() -> None:
    campaign = Campaign.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        name="metrics",
        steps=[StepDraft(subject="Hello", body="Hi", delay_seconds=0)],
    )
    replied_lead, bounced_lead = campaign.add_leads(
        ["a@example.com", "b@example.com"], known_emails=[]
    )
    started, scheduled, _ = campaign.start([replied_lead, bounced_lead], now())
    sent = [started.record_sent(lead, 1, now())[0] for lead in scheduled]
    paused = started.stop_on_reply(sent[0], "positive", now())
    bounced = started.stop_on_reply(sent[1], "bounce", now())
    replied_before = _sample("lead_paused_total", {"reason": "replied"})
    bounced_before = _sample("lead_paused_total", {"reason": "bounced"})

    record_stopped_leads([paused, bounced])

    assert _sample("lead_paused_total", {"reason": "replied"}) == replied_before + 1
    assert _sample("lead_paused_total", {"reason": "bounced"}) == bounced_before


def test_classified_replies_are_counted_by_intent() -> None:
    before = _sample("reply_classified_total", {"intent": "unsubscribe"})

    record_replies_classified(["unsubscribe", "unsubscribe"])

    assert _sample("reply_classified_total", {"intent": "unsubscribe"}) == before + 2
