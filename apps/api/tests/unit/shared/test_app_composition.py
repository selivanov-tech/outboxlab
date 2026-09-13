from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.entrypoints.api import app, create_app


def _paths(application: FastAPI) -> set[str]:
    return {getattr(route, "path", "") for route in application.routes}


def _settings(app_env: str) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://x:x@x/x",
        api_domain="localhost",
        app_env=app_env,  # pyright: ignore[reportArgumentType]
    )


def test_production_serves_campaigns_and_viewer_but_not_test_email() -> None:
    paths = _paths(create_app(_settings("production")))

    assert {
        "/campaigns",
        "/campaigns/{campaign_id}",
        "/campaigns/{campaign_id}/metrics",
        "/mailboxes",
        "/debug/state",
        "/viewer",
        "/mcp",
    } <= paths
    assert "/send-test-email" not in paths


def test_production_rejects_the_workspace_header() -> None:
    with TestClient(create_app(_settings("production"))) as client:
        response = client.get("/campaigns", headers={"X-Workspace-Id": "x"})

    assert response.status_code == 401


def test_non_production_also_serves_the_test_email_route() -> None:
    assert "/send-test-email" in _paths(create_app(_settings("local")))


def test_viewer_page_and_script_are_served() -> None:
    with TestClient(app) as client:
        page = client.get("/viewer/")
        script = client.get("/viewer/viewer.js")

    assert page.status_code == 200
    assert "OutboxLab state viewer" in page.text
    assert script.status_code == 200
    assert "REFRESH_INTERVAL_MS" in script.text
