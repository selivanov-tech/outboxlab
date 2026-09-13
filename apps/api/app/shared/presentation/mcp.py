import httpx2
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.providers.openapi import MCPType, RouteMap

MCP_TAG = "mcp"


async def forward_caller_authorization(request: httpx2.Request) -> None:
    authorization = get_http_headers(include={"authorization"}).get("authorization")
    if authorization:
        request.headers["Authorization"] = authorization


def build_mcp_server(app: FastAPI) -> FastMCP:
    return FastMCP.from_fastapi(
        app=app,
        name="OutboxLab",
        route_maps=[
            RouteMap(tags={MCP_TAG}, mcp_type=MCPType.TOOL),
            RouteMap(mcp_type=MCPType.EXCLUDE),
        ],
        httpx_client_kwargs={
            "event_hooks": {"request": [forward_caller_authorization]}
        },
    )
