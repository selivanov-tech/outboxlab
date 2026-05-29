import uuid
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.identity.application.queries.get_my_workspace import WorkspaceNotFoundError
from app.identity.domain.workspace import Workspace
from app.identity.presentation.routes.workspaces import get_my_workspace_handler
from app.main import app
from app.shared.util.clock import now


class _StubHandler:
    def __init__(self) -> None:
        self.returns: Workspace | None = None
        self.raises: type[Exception] | None = None
        self.called_with: UUID | None = None

    async def execute(self, workspace_id: UUID) -> Workspace:
        self.called_with = workspace_id
        if self.raises is not None:
            raise self.raises()
        assert self.returns is not None
        return self.returns


@pytest.fixture
def stub_handler() -> Iterator[_StubHandler]:
    stub = _StubHandler()
    app.dependency_overrides[get_my_workspace_handler] = lambda: stub
    try:
        yield stub
    finally:
        app.dependency_overrides.pop(get_my_workspace_handler, None)


def test_returns_workspace_for_valid_header(stub_handler: _StubHandler) -> None:
    ws = Workspace(id=uuid.uuid7(), name="acme", created_at=now())
    stub_handler.returns = ws

    with TestClient(app) as client:
        response = client.get(
            "/workspaces/me",
            headers={"X-Workspace-Id": str(ws.id)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(ws.id)
    assert body["name"] == "acme"
    assert stub_handler.called_with == ws.id


def test_returns_401_without_header() -> None:
    with TestClient(app) as client:
        response = client.get("/workspaces/me")
    assert response.status_code == 401


def test_returns_404_when_handler_raises_not_found(
    stub_handler: _StubHandler,
) -> None:
    stub_handler.raises = WorkspaceNotFoundError

    with TestClient(app) as client:
        response = client.get(
            "/workspaces/me",
            headers={"X-Workspace-Id": str(uuid.uuid7())},
        )

    assert response.status_code == 404


def test_returns_400_for_malformed_header_uuid() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/workspaces/me",
            headers={"X-Workspace-Id": "not-a-uuid"},
        )
    assert response.status_code == 400
