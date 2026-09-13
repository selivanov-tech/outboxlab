import uuid
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contexts.mailbox.domain.mailbox import DEFAULT_DAILY_SEND_CAP, Mailbox
from app.shared.util.clock import now


def _make_mailbox(**overrides: object) -> Mailbox:
    defaults = {
        "id": uuid.uuid7(),
        "workspace_id": uuid.uuid7(),
        "email_address": "ops@example.com",
        "last_sync_cursor": None,
        "daily_send_cap": DEFAULT_DAILY_SEND_CAP,
        "created_at": now(),
    }
    defaults.update(overrides)
    return Mailbox(**defaults)


def test_mailbox_is_frozen() -> None:
    mb = _make_mailbox()
    with pytest.raises(ValidationError):
        mb.email_address = "other@example.com"  # type: ignore[misc]


def test_new_assigns_identity_and_lowercases_email() -> None:
    ws_id = uuid.uuid7()
    mb = Mailbox.new(ws_id, "Ops@Example.COM")
    assert isinstance(mb.id, UUID)
    assert mb.workspace_id == ws_id
    assert mb.email_address == "ops@example.com"
    assert mb.last_sync_cursor is None
    assert mb.daily_send_cap == DEFAULT_DAILY_SEND_CAP


def test_new_accepts_an_explicit_daily_send_cap() -> None:
    assert Mailbox.new(uuid.uuid7(), "ops@example.com", 5).daily_send_cap == 5


def test_with_cursor_returns_updated_copy() -> None:
    mb = Mailbox.new(uuid.uuid7(), "ops@example.com")
    advanced = mb.with_cursor("12345")
    assert advanced.last_sync_cursor == "12345"
    assert advanced.id == mb.id
    assert advanced.email_address == mb.email_address
    assert mb.last_sync_cursor is None
