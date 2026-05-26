from fastapi.testclient import TestClient

from app.main import app


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
