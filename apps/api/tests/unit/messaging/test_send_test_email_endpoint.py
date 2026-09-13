import uuid
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.entrypoints.api import app
from app.contexts.messaging.application.commands.send_email import (
    MailboxNotConfiguredError,
    SendEmailCommand,
)
from app.contexts.messaging.domain.outbound_message import OutboundMessage
from app.contexts.messaging.presentation.routes.messaging import send_email_handler


class _StubHandler:
    def __init__(self) -> None:
        self.returns: OutboundMessage | None = None
        self.raises: type[Exception] | None = None
        self.called_with: tuple[SendEmailCommand, UUID] | None = None

    async def execute(
        self, command: SendEmailCommand, workspace_id: UUID
    ) -> OutboundMessage:
        self.called_with = (command, workspace_id)
        if self.raises is not None:
            raise self.raises()
        assert self.returns is not None
        return self.returns


@pytest.fixture
def stub_handler() -> Iterator[_StubHandler]:
    stub = _StubHandler()
    app.dependency_overrides[send_email_handler] = lambda: stub
    try:
        yield stub
    finally:
        app.dependency_overrides.pop(send_email_handler, None)


def _body() -> dict[str, str]:
    return {"to_email": "lead@example.com", "subject": "Hi", "body": "Body"}


def test_returns_outbound_for_valid_request(stub_handler: _StubHandler) -> None:
    workspace_id = uuid.uuid7()
    outbound = OutboundMessage.new(
        workspace_id=workspace_id,
        mailbox_id=uuid.uuid7(),
        to_email="lead@example.com",
        subject="Hi",
        body="Body",
        rfc822_message_id="<abc@example.com>",
    ).sent("gmail-1", "thread-1")
    stub_handler.returns = outbound

    with TestClient(app) as client:
        response = client.post(
            "/send-test-email",
            json=_body(),
            headers={"X-Workspace-Id": str(workspace_id)},
        )

    assert response.status_code == 200
    assert response.json()["provider_message_id"] == "gmail-1"
    assert stub_handler.called_with is not None
    assert stub_handler.called_with[1] == workspace_id


def test_returns_401_without_header(stub_handler: _StubHandler) -> None:
    with TestClient(app) as client:
        response = client.post("/send-test-email", json=_body())
    assert response.status_code == 401


def test_returns_409_when_mailbox_not_configured(stub_handler: _StubHandler) -> None:
    stub_handler.raises = MailboxNotConfiguredError

    with TestClient(app) as client:
        response = client.post(
            "/send-test-email",
            json=_body(),
            headers={"X-Workspace-Id": str(uuid.uuid7())},
        )

    assert response.status_code == 409
