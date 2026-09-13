import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.contexts.campaign.application.process_send_jobs import (
    SendJobNotClaimedError,
    SendJobOutcome,
)
from app.contexts.campaign.presentation.routes.internal_send_jobs import (
    process_send_job_by_id_handler,
)
from app.entrypoints.api import create_app

TOKEN = "internal-test-token"
WORKSPACE_ID = str(uuid.uuid7())


class _StubHandler:
    def __init__(self) -> None:
        self.result: SendJobOutcome = SendJobOutcome.SENT
        self.raises: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> SendJobOutcome:
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return self.result


def _settings(internal_api_token: str = TOKEN) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://x:x@x/x",
        api_domain="localhost",
        app_env="local",
        internal_api_token=internal_api_token,
    )


@pytest.fixture
def stub() -> Iterator[tuple[TestClient, _StubHandler]]:
    settings = _settings()
    app = create_app(settings)
    handler = _StubHandler()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[process_send_job_by_id_handler] = lambda: handler
    with TestClient(app) as client:
        yield client, handler


def _post(client: TestClient, job_id: str, **headers: str) -> Any:
    return client.post(f"/internal/send-jobs/{job_id}/process", headers=headers)


def test_processes_a_claimed_job(stub: tuple[TestClient, _StubHandler]) -> None:
    client, handler = stub
    job_id = str(uuid.uuid7())

    response = client.post(
        f"/internal/send-jobs/{job_id}/process",
        headers={"X-Internal-Token": TOKEN, "X-Workspace-Id": WORKSPACE_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"job_id": job_id, "outcome": "sent"}
    assert str(handler.calls[0]["job_id"]) == job_id
    assert str(handler.calls[0]["workspace_id"]) == WORKSPACE_ID


def test_rejects_a_missing_or_wrong_token(
    stub: tuple[TestClient, _StubHandler],
) -> None:
    client, handler = stub
    job_id = str(uuid.uuid7())

    missing = client.post(
        f"/internal/send-jobs/{job_id}/process",
        headers={"X-Workspace-Id": WORKSPACE_ID},
    )
    wrong = client.post(
        f"/internal/send-jobs/{job_id}/process",
        headers={"X-Internal-Token": "guess", "X-Workspace-Id": WORKSPACE_ID},
    )

    assert (missing.status_code, wrong.status_code) == (401, 401)
    assert handler.calls == []


def test_a_job_that_is_not_claimed_is_a_conflict(
    stub: tuple[TestClient, _StubHandler],
) -> None:
    client, handler = stub
    handler.raises = SendJobNotClaimedError()

    response = client.post(
        f"/internal/send-jobs/{uuid.uuid7()}/process",
        headers={"X-Internal-Token": TOKEN, "X-Workspace-Id": WORKSPACE_ID},
    )

    assert response.status_code == 409


def test_the_route_is_absent_without_a_token() -> None:
    paths = {getattr(route, "path", "") for route in create_app(_settings("")).routes}

    assert "/internal/send-jobs/{job_id}/process" not in paths
