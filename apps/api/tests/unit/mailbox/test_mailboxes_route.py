import uuid
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.contexts.mailbox.application.queries.list_mailboxes import MailboxOverview
from app.contexts.mailbox.domain.mailbox import Mailbox
from app.contexts.mailbox.presentation.routes.mailboxes import list_mailboxes_handler
from app.entrypoints.api import app


class _StubHandler:
    def __init__(self) -> None:
        self.result: list[MailboxOverview] = []
        self.calls: list[UUID] = []

    async def execute(
        self, workspace_id: UUID, moment: datetime
    ) -> list[MailboxOverview]:
        self.calls.append(workspace_id)
        return self.result


@pytest.fixture
def stub() -> Iterator[_StubHandler]:
    handler = _StubHandler()
    app.dependency_overrides[list_mailboxes_handler] = lambda: handler
    try:
        yield handler
    finally:
        app.dependency_overrides.pop(list_mailboxes_handler, None)


def test_lists_mailboxes_with_the_remaining_daily_volume(stub: _StubHandler) -> None:
    workspace_id = uuid.uuid7()
    mailbox = Mailbox.new(workspace_id, "ops@example.com", daily_send_cap=5)
    stub.result = [
        MailboxOverview(mailbox=mailbox, sent_today=7, suppressed_addresses=2)
    ]

    with TestClient(app) as client:
        response = client.get(
            "/mailboxes", headers={"X-Workspace-Id": str(workspace_id)}
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(mailbox.id),
            "email_address": "ops@example.com",
            "daily_send_cap": 5,
            "sent_today": 7,
            "remaining_today": 0,
            "suppressed_addresses": 2,
        }
    ]
    assert stub.calls == [workspace_id]


def test_mailboxes_need_credentials(stub: _StubHandler) -> None:
    with TestClient(app) as client:
        assert client.get("/mailboxes").status_code == 401
