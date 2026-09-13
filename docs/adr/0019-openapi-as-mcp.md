# ADR 0019 — The API is exposed to MCP clients by generating tools from its OpenAPI document

**Status:** accepted (Step 6)

## Context

The locked default for Step 6 was "OpenAPI-as-MCP": no hand-written tools, a tool surface that follows the HTTP API, and a workspace API key checked on every call. Claude Code and Claude Desktop connect to remote MCP servers by URL plus headers; they have no client-side "OpenAPI" server type, so the conversion must happen on the server.

A spike ran first, before any route changed:

- FastMCP 4.0.3 installs and runs on Python 3.14 with the project's pins.
- `FastMCP.from_fastapi(app)` builds tools from the app's OpenAPI document and calls the routes in-process through an ASGI transport, so every call passes the API middleware.
- By default it does **not** forward the MCP caller's `Authorization` header: a call with a valid key reached the route without it and got `401`.
- An httpx request hook that copies `get_http_headers(include={"authorization"})` onto the outgoing request forwards the key; without a client header the call is still `401`.

## Decision

- `app/shared/presentation/mcp.py` builds the MCP server with `FastMCP.from_fastapi`:
  - **Route maps:** routes tagged `mcp` become tools; every other route is excluded (health, version, debug, test email, internal routes, the viewer).
  - **Names:** explicit `operation_id`s on the routes (`create_campaign`, `add_leads_to_campaign`, `start_campaign`, `list_campaigns`, `get_campaign`, `get_campaign_metrics`, `list_mailboxes`). Route `summary`, response models with field descriptions and documented error responses become the tool descriptions.
  - **Auth:** the request hook forwards the caller's `Authorization` header to each in-process call. The workspace middleware from [ADR 0017](0017-workspace-api-keys.md) checks the key on every tool call.
- `create_app` mounts the MCP app at `/mcp/` (streamable HTTP) in **every environment**, and chains its lifespan with the API's. The local and production client setups are the same.
- Two thin read routes were added because the demo needs them: `GET /campaigns/{id}/metrics` (campaign context) and `GET /mailboxes` (mailbox context, which reaches messaging only through its own port and an adapter). Starting a campaign that has no leads is now `422`.
- The fallback — the lower-level `mcp` SDK with thin hand-written tools over the same handlers — was not needed.

## Consequences

- No domain logic in the MCP layer, and no second list of operations: adding a tool means tagging a route.
- The tool list (names and schemas) is readable without a key; only tool calls are authorized. This matches the public OpenAPI document of the same API.
- One more runtime dependency (`fastmcp`, a large lock diff); it is isolated in one presentation module.
- Streamable HTTP runs through the same Starlette middleware stack as the API; an end-to-end test serves the production app with uvicorn and calls a tool with and without a key.
- Not built: OAuth for MCP clients (Claude Desktop custom connectors expect it), per-key scopes, the stretch tools (copy generation, reply analysis, send-time advice), campaign pause / resume.
