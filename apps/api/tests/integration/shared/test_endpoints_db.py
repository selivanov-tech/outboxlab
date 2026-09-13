import uuid

from fastapi.testclient import TestClient

from app.entrypoints.api import app

WORKSPACE_ID = str(uuid.uuid7())


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_debug_state_requires_credentials() -> None:
    with TestClient(app) as client:
        response = client.get("/debug/state")
    assert response.status_code == 401


def test_debug_state_is_scoped_to_the_workspace() -> None:
    with TestClient(app) as client:
        response = client.get("/debug/state", headers={"X-Workspace-Id": WORKSPACE_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "ok"
    assert body["workspace_id"] == WORKSPACE_ID
    assert body["outbound_count"] == 0
    assert body["inbound_count"] == 0
    assert body["intents"] == {}
    assert body["leads"] == {}
    assert body["send_jobs"] == {}
    assert body["recent_events"] == []
    assert body["mailbox_last_sync_cursor"] is None
