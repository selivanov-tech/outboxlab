from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.shared.presentation.routes.version import router


def test_version_endpoint_returns_expected_fields() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql+asyncpg://x:x@x/x",
        api_domain="api.test.local",
        app_env="ci",
        git_sha="abc1234",
    )

    with TestClient(app) as client:
        response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert body == {"version": "0.0.1", "git_sha": "abc1234", "app_env": "ci"}
