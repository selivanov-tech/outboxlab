import uuid

import pytest
from pydantic import ValidationError

from app.contexts.messaging.domain.inbound_message import InboundMessage
from app.contexts.messaging.domain.intent import Intent
from app.shared.util.clock import now


def _new() -> InboundMessage:
    return InboundMessage.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        provider_message_id="m1",
        provider_thread_id="t1",
        from_email="lead@example.com",
        subject="Re: Hi",
        snippet="yes let's talk",
        in_reply_to_header="<abc@example.com>",
        references_header="<abc@example.com>",
        received_at=now(),
    )


def test_new_starts_unmatched_and_unclassified() -> None:
    msg = _new()
    assert msg.matched_outbound_id is None
    assert msg.intent is None


def test_matched_then_classified_in_copies() -> None:
    out_id = uuid.uuid7()
    matched = _new().matched_to(out_id)
    classified = matched.classified_as(Intent.POSITIVE)
    assert matched.matched_outbound_id == out_id
    assert classified.intent is Intent.POSITIVE
    assert classified.matched_outbound_id == out_id


def test_is_frozen() -> None:
    msg = _new()
    with pytest.raises(ValidationError):
        msg.snippet = "changed"  # type: ignore[misc]
