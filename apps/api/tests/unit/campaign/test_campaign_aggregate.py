import uuid
from datetime import timedelta

import pytest

from app.contexts.campaign.domain.campaign import Campaign, CampaignStatus, StepDraft
from app.contexts.campaign.domain.errors import (
    CampaignHasNoStepsError,
    CampaignNotActiveError,
    LeadNotInCampaignError,
    LeadTransitionError,
    NegativeStepDelayError,
)
from app.contexts.campaign.domain.lead import Lead, LeadState, StopReason
from app.contexts.campaign.domain.send_job import SendJobStatus, next_retry_at
from app.shared.util.clock import now

STEP_TWO_DELAY = 120


def _campaign(steps: int = 2) -> Campaign:
    drafts = [
        StepDraft(subject="Hello", body="First touch", delay_seconds=0),
        StepDraft(subject="Re: Hello", body="Follow-up", delay_seconds=STEP_TWO_DELAY),
    ][:steps]
    return Campaign.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        name="Q3 outreach",
        steps=drafts,
    )


def _started_with_lead(steps: int = 2) -> tuple[Campaign, Lead]:
    campaign = _campaign(steps)
    (lead,) = campaign.add_leads(["lead@example.com"], known_emails=[])
    started, (scheduled,), _ = campaign.start([lead], now())
    return started, scheduled


def test_new_numbers_steps_and_starts_as_draft() -> None:
    campaign = _campaign()

    assert campaign.status is CampaignStatus.DRAFT
    assert [step.position for step in campaign.steps] == [1, 2]
    assert campaign.steps[1].delay_seconds == STEP_TWO_DELAY


def test_new_requires_at_least_one_step() -> None:
    with pytest.raises(CampaignHasNoStepsError):
        Campaign.new(
            workspace_id=uuid.uuid7(), mailbox_id=uuid.uuid7(), name="x", steps=[]
        )


def test_new_rejects_negative_delay() -> None:
    with pytest.raises(NegativeStepDelayError):
        Campaign.new(
            workspace_id=uuid.uuid7(),
            mailbox_id=uuid.uuid7(),
            name="x",
            steps=[StepDraft(subject="s", body="b", delay_seconds=-1)],
        )


def test_add_leads_normalizes_and_skips_duplicates() -> None:
    campaign = _campaign()

    leads = campaign.add_leads(
        [" Lead@Example.com ", "lead@example.com", "", "known@example.com", "b@x.io"],
        known_emails=["known@example.com"],
    )

    assert [lead.email for lead in leads] == ["lead@example.com", "b@x.io"]
    assert all(lead.state is LeadState.PENDING for lead in leads)
    assert all(lead.campaign_id == campaign.id for lead in leads)


def test_start_activates_and_schedules_first_step() -> None:
    campaign = _campaign()
    (lead,) = campaign.add_leads(["lead@example.com"], known_emails=[])
    moment = now()

    started, scheduled, jobs = campaign.start([lead], moment)

    assert started.status is CampaignStatus.ACTIVE
    assert [item.state for item in scheduled] == [LeadState.SCHEDULED]
    (job,) = jobs
    assert job.status is SendJobStatus.PENDING
    assert job.scheduled_at == moment
    assert job.mailbox_id == campaign.mailbox_id
    assert job.payload.step_position == 1
    assert job.payload.to_email == "lead@example.com"
    assert job.payload.subject == "Hello"
    assert job.payload.campaign_id == campaign.id


def test_start_is_idempotent_for_an_active_campaign() -> None:
    started, _ = _started_with_lead()

    again, scheduled, jobs = started.start([], now())

    assert again is started
    assert scheduled == []
    assert jobs == []


def test_schedule_requires_active_campaign() -> None:
    campaign = _campaign()
    (lead,) = campaign.add_leads(["lead@example.com"], known_emails=[])

    with pytest.raises(CampaignNotActiveError):
        campaign.schedule([lead], now())


def test_schedule_rejects_a_lead_that_is_not_pending() -> None:
    started, scheduled = _started_with_lead()

    with pytest.raises(LeadTransitionError):
        started.schedule([scheduled], now())


def test_schedule_rejects_a_lead_from_another_campaign() -> None:
    started, _ = _started_with_lead()
    other = _campaign()
    (stranger,) = other.add_leads(["x@example.com"], known_emails=[])

    with pytest.raises(LeadNotInCampaignError):
        started.schedule([stranger], now())


def test_record_sent_moves_to_sent_and_schedules_next_step() -> None:
    started, lead = _started_with_lead()
    sent_at = now()

    sent, next_job = started.record_sent(lead, 1, sent_at)

    assert sent.state is LeadState.SENT
    assert sent.steps_sent == 1
    assert next_job is not None
    assert next_job.payload.step_position == 2
    assert next_job.scheduled_at == sent_at + timedelta(seconds=STEP_TWO_DELAY)


def test_record_sent_on_last_step_finishes_the_lead() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())

    done, next_job = started.record_sent(sent, 2, now())

    assert done.state is LeadState.DONE
    assert done.steps_sent == 2
    assert next_job is None


def test_record_sent_rejects_a_repeated_step() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())

    assert not started.accepts_send(sent, 1)
    with pytest.raises(LeadTransitionError):
        started.record_sent(sent, 1, now())


def test_positive_reply_pauses_the_lead() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())

    paused = started.stop_on_reply(sent, "positive", now())

    assert paused.state is LeadState.PAUSED
    assert paused.stop_reason is StopReason.REPLIED
    assert paused.reply_intent == "positive"
    assert not started.accepts_send(paused, 2)


def test_unsubscribe_reply_pauses_with_unsubscribed_reason() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())

    paused = started.stop_on_reply(sent, "unsubscribe", now())

    assert paused.state is LeadState.PAUSED
    assert paused.stop_reason is StopReason.UNSUBSCRIBED


def test_bounce_fails_the_lead() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())

    failed = started.stop_on_reply(sent, "bounce", now())

    assert failed.state is LeadState.FAILED
    assert failed.stop_reason is StopReason.BOUNCED


def test_reply_after_the_last_step_still_pauses() -> None:
    started, lead = _started_with_lead(steps=1)
    done, _ = started.record_sent(lead, 1, now())

    paused = started.stop_on_reply(done, "negative", now())

    assert paused.state is LeadState.PAUSED


def test_reply_to_a_stopped_lead_changes_nothing() -> None:
    started, lead = _started_with_lead()
    sent, _ = started.record_sent(lead, 1, now())
    paused = started.stop_on_reply(sent, "positive", now())

    assert started.stop_on_reply(paused, "bounce", now()) is paused


def test_reply_before_any_send_is_rejected() -> None:
    started, scheduled = _started_with_lead()

    with pytest.raises(LeadTransitionError):
        started.stop_on_reply(scheduled, "positive", now())


def test_fail_lead_from_scheduled() -> None:
    started, scheduled = _started_with_lead()

    failed = started.fail_lead(scheduled, StopReason.SUPPRESSED, now())

    assert failed.state is LeadState.FAILED
    assert failed.stop_reason is StopReason.SUPPRESSED


def test_fail_lead_rejects_a_done_lead() -> None:
    started, lead = _started_with_lead(steps=1)
    done, _ = started.record_sent(lead, 1, now())

    with pytest.raises(LeadTransitionError):
        started.fail_lead(done, StopReason.SEND_FAILED, now())


def test_next_retry_at_backs_off_then_gives_up() -> None:
    moment = now()

    assert next_retry_at(1, moment) == moment + timedelta(seconds=60)
    assert next_retry_at(2, moment) == moment + timedelta(seconds=120)
    assert next_retry_at(3, moment) is None
