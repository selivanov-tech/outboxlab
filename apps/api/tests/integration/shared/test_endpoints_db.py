from fastapi.testclient import TestClient

from app.entrypoints.api import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_debug_state_reports_db_ok_and_workspace_count() -> None:
    with TestClient(app) as client:
        response = client.get("/debug/state")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "ok"
    assert isinstance(body["workspace_count"], int)
    assert body["workspace_count"] >= 0


def test_debug_state_reports_messaging_counts() -> None:
    with TestClient(app) as client:
        response = client.get("/debug/state")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["outbound_count"], int)
    assert isinstance(body["inbound_count"], int)
    assert isinstance(body["intents"], dict)
    assert isinstance(body["recent_events"], list)
    assert isinstance(body["leads"], dict)
    assert isinstance(body["send_jobs"], dict)
    assert "mailbox_last_sync_cursor" in body
