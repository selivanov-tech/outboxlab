import uuid
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.shared.presentation.dependencies import require_workspace
from app.shared.presentation.middleware import WorkspaceContextMiddleware

KEY_WORKSPACE = uuid.uuid7()
VALID_KEY = "olab_a1b2c3d4e5f6_secret"


async def _resolve(raw_key: str) -> UUID | None:
    return KEY_WORKSPACE if raw_key == VALID_KEY else None


def _client(*, accept_workspace_header: bool) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        WorkspaceContextMiddleware,
        resolve_api_key=_resolve,
        accept_workspace_header=accept_workspace_header,
    )

    @app.get("/whoami")
    async def whoami(
        workspace_id: Annotated[UUID, Depends(require_workspace)],
    ) -> dict[str, str]:
        return {"workspace_id": str(workspace_id)}

    @app.get("/open")
    async def open_route() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app)


def test_a_valid_api_key_sets_the_workspace() -> None:
    with _client(accept_workspace_header=False) as client:
        response = client.get(
            "/whoami", headers={"Authorization": f"Bearer {VALID_KEY}"}
        )

    assert response.status_code == 200
    assert response.json() == {"workspace_id": str(KEY_WORKSPACE)}


def test_an_invalid_api_key_is_rejected_on_every_route() -> None:
    with _client(accept_workspace_header=True) as client:
        response = client.get("/open", headers={"Authorization": "Bearer olab_x_y"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


def test_the_workspace_header_works_where_it_is_accepted() -> None:
    workspace_id = uuid.uuid7()

    with _client(accept_workspace_header=True) as client:
        response = client.get("/whoami", headers={"X-Workspace-Id": str(workspace_id)})

    assert response.json() == {"workspace_id": str(workspace_id)}


def test_the_workspace_header_is_rejected_where_only_keys_are_accepted() -> None:
    with _client(accept_workspace_header=False) as client:
        response = client.get("/whoami", headers={"X-Workspace-Id": str(uuid.uuid7())})

    assert response.status_code == 401


def test_the_api_key_wins_over_the_workspace_header() -> None:
    with _client(accept_workspace_header=True) as client:
        response = client.get(
            "/whoami",
            headers={
                "Authorization": f"Bearer {VALID_KEY}",
                "X-Workspace-Id": str(uuid.uuid7()),
            },
        )

    assert response.json() == {"workspace_id": str(KEY_WORKSPACE)}


def test_no_credentials_reach_the_route_and_fail_there() -> None:
    with _client(accept_workspace_header=True) as client:
        assert client.get("/open").status_code == 200
        assert client.get("/whoami").status_code == 401
