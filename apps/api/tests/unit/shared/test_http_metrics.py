import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.contexts.campaign.application.errors import CampaignNotFoundError
from app.contexts.campaign.presentation.routes.campaigns import get_campaign_handler
from app.entrypoints.api import app

HEADERS = {"X-Workspace-Id": str(uuid.uuid7())}


def _requests(route: str, status: str, method: str = "GET") -> float:
    value = REGISTRY.get_sample_value(
        "http_requests_total", {"method": method, "route": route, "status": status}
    )
    return value or 0.0


class _NotFound:
    async def execute(self, campaign_id: uuid.UUID) -> None:
        raise CampaignNotFoundError


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_campaign_handler] = lambda: _NotFound()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_campaign_handler, None)


def test_requests_are_labelled_with_the_route_template(client: TestClient) -> None:
    before = _requests("/campaigns/{campaign_id}", "404")

    client.get(f"/campaigns/{uuid.uuid7()}", headers=HEADERS)
    client.get(f"/campaigns/{uuid.uuid7()}", headers=HEADERS)

    assert _requests("/campaigns/{campaign_id}", "404") == before + 2


def test_mounted_apps_and_unknown_paths_keep_labels_bounded(client: TestClient) -> None:
    viewer_before = _requests("/viewer", "200")
    unmatched_before = _requests("unmatched", "404")

    client.get("/viewer/viewer.js")
    client.get(f"/no-such-route/{uuid.uuid7()}")

    assert _requests("/viewer", "200") == viewer_before + 1
    assert _requests("unmatched", "404") == unmatched_before + 1


def test_metrics_endpoint_exposes_counters_without_counting_itself(
    client: TestClient,
) -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert (
        'http_requests_total{method="GET",route="/health",status="200"}'
        in response.text
    )
    assert "emails_sent_total" in response.text
    assert 'route="/metrics"' not in response.text
