import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest_asyncio
import uvicorn
from fastapi import FastAPI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from app.config import Settings
from app.contexts.campaign.presentation.routes.campaigns import list_campaigns_handler
from app.entrypoints.api import create_app
from app.shared.presentation.mcp import build_mcp_server

WORKSPACE_ID = uuid.uuid7()
VALID_KEY = "olab_a1b2c3d4e5f6_secret"
EXPECTED_TOOLS = {
    "create_campaign",
    "list_campaigns",
    "get_campaign",
    "add_leads_to_campaign",
    "start_campaign",
    "get_campaign_metrics",
    "list_mailboxes",
}


async def _resolve(raw_key: str) -> UUID | None:
    return WORKSPACE_ID if raw_key == VALID_KEY else None


def _production_app() -> FastAPI:
    return create_app(
        Settings(
            database_url="postgresql+asyncpg://x:x@x/x",
            api_domain="localhost",
            app_env="production",
        ),
        resolve_api_key=_resolve,
    )


class _ListCampaignsStub:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self) -> list[Any]:
        self.calls += 1
        return []


@pytest_asyncio.fixture
async def served() -> AsyncIterator[tuple[str, _ListCampaignsStub]]:
    app = _production_app()
    stub = _ListCampaignsStub()
    app.dependency_overrides[list_campaigns_handler] = lambda: stub
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", ws="none")
    )
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}/mcp/", stub
    finally:
        server.should_exit = True
        await task


async def test_only_business_routes_become_tools() -> None:
    async with Client(build_mcp_server(_production_app())) as client:
        tools = {tool.name for tool in await client.list_tools()}

    assert tools == EXPECTED_TOOLS


async def test_a_tool_call_carries_the_callers_api_key_to_the_api(
    served: tuple[str, _ListCampaignsStub],
) -> None:
    url, stub = served
    transport = StreamableHttpTransport(
        url, headers={"Authorization": f"Bearer {VALID_KEY}"}
    )

    async with Client(transport) as client:
        result = await client.call_tool("list_campaigns", {}, raise_on_error=False)

    assert not result.is_error
    assert stub.calls == 1


async def test_a_tool_call_without_a_key_is_refused_by_the_api(
    served: tuple[str, _ListCampaignsStub],
) -> None:
    url, stub = served

    async with Client(StreamableHttpTransport(url)) as client:
        result = await client.call_tool("list_campaigns", {}, raise_on_error=False)

    assert result.is_error
    assert "401" in str(result.content)
    assert stub.calls == 0
