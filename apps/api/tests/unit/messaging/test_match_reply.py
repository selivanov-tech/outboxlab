import uuid
from typing import Any

from app.contexts.messaging.application.matching import match_reply
from app.contexts.messaging.application.ports.email_receiver import FetchedMessage
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.shared.util.clock import now


def _candidate(
    rfc822_message_id: str,
    *,
    subject: str = "Hi",
    provider_thread_id: str = "t-out",
    to_email: str = "lead@example.com",
) -> OutboundMessage:
    base = OutboundMessage.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        to_email=to_email,
        subject=subject,
        body="b",
        rfc822_message_id=rfc822_message_id,
    )
    return base.sent("gmail-x", provider_thread_id)


def _inbound(**overrides: Any) -> FetchedMessage:
    defaults: dict[str, Any] = {
        "provider_message_id": "m-in",
        "provider_thread_id": "t-in",
        "from_email": "lead@example.com",
        "subject": "Re: Hi",
        "snippet": "...",
        "in_reply_to_header": None,
        "references_header": None,
        "received_at": now(),
    }
    defaults.update(overrides)
    return FetchedMessage(**defaults)


def test_exact_in_reply_to_match() -> None:
    candidate = _candidate("<abc@example.com>")
    inbound = _inbound(in_reply_to_header="<abc@example.com>")
    assert match_reply(inbound, [candidate]) is candidate


def test_references_chain_among_several() -> None:
    candidate = _candidate("<abc@example.com>")
    inbound = _inbound(
        references_header="<x@example.com> <abc@example.com> <y@example.com>"
    )
    assert match_reply(inbound, [candidate]) is candidate


def test_references_with_folded_whitespace() -> None:
    candidate = _candidate("<abc@example.com>")
    inbound = _inbound(references_header="  <x@example.com>\r\n   <abc@example.com>  ")
    assert match_reply(inbound, [candidate]) is candidate


def test_in_reply_to_without_angle_brackets() -> None:
    candidate = _candidate("<abc@example.com>")
    inbound = _inbound(in_reply_to_header="abc@example.com")
    assert match_reply(inbound, [candidate]) is candidate


def test_thread_id_fallback() -> None:
    candidate = _candidate("<abc@example.com>", provider_thread_id="shared-thread")
    inbound = _inbound(provider_thread_id="shared-thread", subject="Unrelated")
    assert match_reply(inbound, [candidate]) is candidate


def test_subject_fallback_strips_re_prefix() -> None:
    candidate = _candidate("<abc@example.com>", subject="Weekly sync")
    inbound = _inbound(subject="Re: Weekly sync", provider_thread_id="t-other")
    assert match_reply(inbound, [candidate]) is candidate


def test_no_match_returns_none() -> None:
    candidate = _candidate(
        "<abc@example.com>", subject="Hi", provider_thread_id="t-out"
    )
    inbound = _inbound(
        in_reply_to_header="<other@example.com>",
        references_header=None,
        provider_thread_id="t-other",
        subject="Completely different",
    )
    assert match_reply(inbound, [candidate]) is None


def test_subject_fallback_requires_the_same_address() -> None:
    other_lead = _candidate(
        "<other@example.com>", subject="Weekly sync", to_email="other@example.com"
    )
    same_lead = _candidate(
        "<same@example.com>", subject="Weekly sync", to_email="Lead@Example.com"
    )
    inbound = _inbound(subject="Re: Weekly sync", provider_thread_id="t-other")

    assert match_reply(inbound, [other_lead]) is None
    assert match_reply(inbound, [other_lead, same_lead]) is same_lead
