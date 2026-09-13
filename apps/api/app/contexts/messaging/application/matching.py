import re

from app.contexts.messaging.application.ports.email_receiver import FetchedMessage
from app.contexts.messaging.domain.outbound_message import OutboundMessage

_SUBJECT_PREFIX = re.compile(r"^(re|fwd|fw)\s*:\s*", re.IGNORECASE)


def match_reply(
    inbound: FetchedMessage, candidates: list[OutboundMessage]
) -> OutboundMessage | None:
    by_message_id = {
        normalized: candidate
        for candidate in candidates
        if (normalized := _normalize_message_id(candidate.rfc822_message_id))
    }

    in_reply_to = _normalize_message_id(inbound.in_reply_to_header)
    if in_reply_to is not None and in_reply_to in by_message_id:
        return by_message_id[in_reply_to]

    for reference in _reference_ids(inbound.references_header):
        if reference in by_message_id:
            return by_message_id[reference]

    by_thread = {
        candidate.provider_thread_id: candidate
        for candidate in candidates
        if candidate.provider_thread_id is not None
    }
    if inbound.provider_thread_id in by_thread:
        return by_thread[inbound.provider_thread_id]

    inbound_subject = _normalize_subject(inbound.subject)
    if inbound_subject:
        for candidate in candidates:
            if (
                candidate.to_email.lower() == inbound.from_email.lower()
                and _normalize_subject(candidate.subject) == inbound_subject
            ):
                return candidate

    return None


def _normalize_message_id(message_id: str | None) -> str | None:
    if message_id is None:
        return None
    stripped = message_id.strip().strip("<>").strip().lower()
    return stripped or None


def _reference_ids(references_header: str | None) -> list[str]:
    if not references_header:
        return []
    ids = []
    for token in references_header.split():
        normalized = _normalize_message_id(token)
        if normalized is not None:
            ids.append(normalized)
    return ids


def _normalize_subject(subject: str) -> str:
    text = subject.strip()
    while True:
        stripped = _SUBJECT_PREFIX.sub("", text, count=1).strip()
        if stripped == text:
            break
        text = stripped
    return text.lower()
