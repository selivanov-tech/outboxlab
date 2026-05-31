import uuid

import pytest
from pydantic import ValidationError

from app.contexts.messaging.domain.outbound_message import OutboundMessage


def _new() -> OutboundMessage:
    return OutboundMessage.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id="<abc@example.com>",
    )


def test_new_starts_unsent() -> None:
    msg = _new()
    assert msg.provider_message_id is None
    assert msg.provider_thread_id is None
    assert msg.rfc822_message_id == "<abc@example.com>"


def test_sent_records_gmail_ids_in_a_copy() -> None:
    original = _new()
    sent = original.sent("gmail-1", "thread-1")
    assert sent.provider_message_id == "gmail-1"
    assert sent.provider_thread_id == "thread-1"
    assert sent.id == original.id
    assert original.provider_message_id is None


def test_is_frozen() -> None:
    msg = _new()
    with pytest.raises(ValidationError):
        msg.subject = "changed"  # type: ignore[misc]
