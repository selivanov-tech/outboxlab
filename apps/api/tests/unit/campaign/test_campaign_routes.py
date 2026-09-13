import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contexts.campaign.application.commands.add_leads import AddLeadsResult
from app.contexts.campaign.application.commands.start_campaign import (
    StartCampaignResult,
)
from app.contexts.campaign.application.errors import (
    CampaignNotFoundError,
    MailboxNotConnectedError,
)
from app.contexts.campaign.application.queries.get_campaign import (
    CampaignDetail,
    LeadView,
)
from app.contexts.campaign.application.queries.list_campaigns import CampaignSummary
from app.contexts.campaign.domain.campaign import Campaign, StepDraft
from app.contexts.campaign.domain.lead import LeadState
from app.contexts.campaign.presentation.routes.campaigns import (
    add_leads_handler,
    create_campaign_handler,
    get_campaign_handler,
    list_campaigns_handler,
    start_campaign_handler,
)
from app.entrypoints.api import app
from app.shared.util.clock import now

WORKSPACE_HEADERS = {"X-Workspace-Id": str(uuid.uuid7())}


class _StubHandler:
    def __init__(self) -> None:
        self.result: Any = None
        self.raises: Exception | None = None
        self.calls: list[tuple[Any, ...]] = []

    async def execute(self, *args: Any) -> Any:
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return self.result


@pytest.fixture
def stub() -> Iterator[Callable[[Callable[..., Any]], _StubHandler]]:
    installed: list[Callable[..., Any]] = []

    def install(factory: Callable[..., Any]) -> _StubHandler:
        handler = _StubHandler()
        app.dependency_overrides[factory] = lambda: handler
        installed.append(factory)
        return handler

    yield install
    for factory in installed:
        app.dependency_overrides.pop(factory, None)


def _campaign() -> Campaign:
    return Campaign.new(
        workspace_id=uuid.uuid7(),
        mailbox_id=uuid.uuid7(),
        name="Q3 outreach",
        steps=[
            StepDraft(subject="Hello", body="First", delay_seconds=0),
            StepDraft(subject="Re: Hello", body="Second", delay_seconds=120),
        ],
    )


def _create_body() -> dict[str, object]:
    return {
        "name": "Q3 outreach",
        "steps": [
            {"subject": "Hello", "body": "First", "delay_seconds": 0},
            {"subject": "Re: Hello", "body": "Second", "delay_seconds": 120},
        ],
    }


def test_create_campaign_returns_201(stub: Callable[..., _StubHandler]) -> None:
    handler = stub(create_campaign_handler)
    handler.result = _campaign()

    with TestClient(app) as client:
        response = client.post(
            "/campaigns", json=_create_body(), headers=WORKSPACE_HEADERS
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert [step["position"] for step in body["steps"]] == [1, 2]
    command, workspace_id = handler.calls[0]
    assert len(command.steps) == 2
    assert str(workspace_id) == WORKSPACE_HEADERS["X-Workspace-Id"]


def test_create_campaign_without_steps_is_422(
    stub: Callable[..., _StubHandler],
) -> None:
    stub(create_campaign_handler)

    with TestClient(app) as client:
        response = client.post(
            "/campaigns",
            json={"name": "x", "steps": []},
            headers=WORKSPACE_HEADERS,
        )

    assert response.status_code == 422


def test_create_campaign_without_mailbox_is_409(
    stub: Callable[..., _StubHandler],
) -> None:
    stub(create_campaign_handler).raises = MailboxNotConnectedError()

    with TestClient(app) as client:
        response = client.post(
            "/campaigns", json=_create_body(), headers=WORKSPACE_HEADERS
        )

    assert response.status_code == 409


def test_campaign_routes_require_the_workspace_header(
    stub: Callable[..., _StubHandler],
) -> None:
    stub(list_campaigns_handler)

    with TestClient(app) as client:
        response = client.get("/campaigns")

    assert response.status_code == 401


def test_list_campaigns_includes_lead_counts(
    stub: Callable[..., _StubHandler],
) -> None:
    campaign = _campaign()
    stub(list_campaigns_handler).result = [
        CampaignSummary(
            campaign=campaign,
            lead_counts={LeadState.SENT: 2, LeadState.PAUSED: 1},
        )
    ]

    with TestClient(app) as client:
        response = client.get("/campaigns", headers=WORKSPACE_HEADERS)

    assert response.status_code == 200
    (summary,) = response.json()
    assert summary["id"] == str(campaign.id)
    assert summary["lead_counts"] == {"sent": 2, "paused": 1}


def test_get_campaign_returns_leads_with_next_send_at(
    stub: Callable[..., _StubHandler],
) -> None:
    campaign = _campaign()
    (lead,) = campaign.add_leads(["lead@example.com"], known_emails=[])
    next_send_at = now()
    stub(get_campaign_handler).result = CampaignDetail(
        campaign=campaign,
        leads=[LeadView(lead=lead, next_send_at=next_send_at)],
    )

    with TestClient(app) as client:
        response = client.get(f"/campaigns/{campaign.id}", headers=WORKSPACE_HEADERS)

    assert response.status_code == 200
    (lead_body,) = response.json()["leads"]
    assert lead_body["email"] == "lead@example.com"
    assert lead_body["state"] == "pending"
    assert lead_body["next_send_at"] is not None


def test_get_unknown_campaign_is_404(stub: Callable[..., _StubHandler]) -> None:
    stub(get_campaign_handler).raises = CampaignNotFoundError()

    with TestClient(app) as client:
        response = client.get(f"/campaigns/{uuid.uuid7()}", headers=WORKSPACE_HEADERS)

    assert response.status_code == 404


def test_add_leads_returns_counts(stub: Callable[..., _StubHandler]) -> None:
    handler = stub(add_leads_handler)
    handler.result = AddLeadsResult(added=1, skipped=1, scheduled=0)

    with TestClient(app) as client:
        response = client.post(
            f"/campaigns/{uuid.uuid7()}/leads",
            json={"emails": ["a@example.com", "a@example.com"]},
            headers=WORKSPACE_HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == {"added": 1, "skipped": 1, "scheduled": 0}
    assert handler.calls[0][1] == ["a@example.com", "a@example.com"]


def test_add_leads_rejects_an_invalid_email(
    stub: Callable[..., _StubHandler],
) -> None:
    stub(add_leads_handler)

    with TestClient(app) as client:
        response = client.post(
            f"/campaigns/{uuid.uuid7()}/leads",
            json={"emails": ["not-an-email"]},
            headers=WORKSPACE_HEADERS,
        )

    assert response.status_code == 422


def test_start_campaign_returns_the_scheduled_count(
    stub: Callable[..., _StubHandler],
) -> None:
    campaign = _campaign()
    started, _, _ = campaign.start([], now())
    stub(start_campaign_handler).result = StartCampaignResult(
        campaign=started, scheduled=3
    )

    with TestClient(app) as client:
        response = client.post(
            f"/campaigns/{campaign.id}/start", headers=WORKSPACE_HEADERS
        )

    assert response.status_code == 200
    assert response.json() == {"status": "active", "scheduled": 3}


def test_start_unknown_campaign_is_404(stub: Callable[..., _StubHandler]) -> None:
    stub(start_campaign_handler).raises = CampaignNotFoundError()

    with TestClient(app) as client:
        response = client.post(
            f"/campaigns/{uuid.uuid7()}/start", headers=WORKSPACE_HEADERS
        )

    assert response.status_code == 404
