# Step 6 — MCP server

[← Back to the plan](README.md)

**Status: code merged** — [PR #8](https://github.com/selivanov-tech/outboxlab/pull/8). The demo with Claude Desktop / Claude Code against a running API is recorded by hand.

## Goal

Let an AI agent (Claude Desktop / Claude Code) drive campaign use cases through MCP, with zero domain logic in the MCP layer.

## Success signal

MCP works locally through Claude Desktop / Claude Code; the demo is recorded.

Covered in CI by `tests/unit/shared/test_mcp_server.py`. It lists exactly the seven tools. It serves the production app with uvicorn and calls `list_campaigns` over streamable HTTP. With the API key the call reaches the handler; without a key it comes back as a `401` tool error.

## Decision: OpenAPI-as-MCP (as built)

See [ADR 0019](../adr/0019-openapi-as-mcp.md) and the client guide in [`docs/mcp.md`](../mcp.md).

1. **Spike first.** FastMCP 4.0.3 works on Python 3.14 with the project's pins. `from_fastapi` calls routes in-process but does not forward the caller's `Authorization`; a request hook fixes that. The lower-level SDK fallback was not needed.
2. **Tools are tagged routes.** Routes tagged `mcp` become tools, named by explicit `operation_id`s; everything else is excluded.
3. **One credential.** The workspace API key from Step 4 is forwarded on every tool call and checked by the normal middleware.
4. **Mounted everywhere.** `/mcp/` exists in every environment behind the key, so the local and production client setups are the same.

## Checklist

- [x] Auth through a workspace API key checked on every call; it resolves the workspace id and sets it in context.
- [x] Basic error handling: invalid campaign (`404`), mailbox not connected (`409`), no leads (`422` on start).
- [x] Example config for Claude Desktop / Claude Code — [`docs/mcp.md`](../mcp.md).
- [ ] Short demo: the agent creates a campaign, adds leads, and reads metrics — manual.

## What was built

- `app/shared/presentation/mcp.py`: `build_mcp_server(app)` with tag route maps and the `Authorization` forwarding hook; `create_app` mounts it at `/mcp/` and chains the lifespans.
- Operation ids, tags, summaries and documented errors on the campaign routes; `GET /campaigns/{id}/metrics`.
- Mailbox context: `GET /mailboxes`, `ListMailboxesHandler`, `MailboxActivityPort` with a messaging adapter (sent today, suppressed addresses).
- `StartCampaignHandler` rejects a draft campaign without leads.
- `fastmcp` 4.0.3 dependency.
- Tests: tool list, the HTTP chain with and without a key, metrics and mailbox handlers against the database, the new routes, start without leads.

## Changes compared with the plan

- The workspace API key was built in Step 4, not here.
- `add_leads_to_campaign` instead of `add_leads`, to read well as a tool name.
- `pause_campaign` / `resume_campaign` from the fallback list are not built; the campaign has no pause state yet.
- `/mcp/` is mounted in production too, behind the key.

## Try it locally

1. `make up`, `make migrate`, `make seed`, then `make api-key` and copy the key once.
2. Add the server to Claude Code: `claude mcp add --transport http outboxlab https://<api-domain>/mcp/ --header "Authorization: Bearer <api-key>"`.
3. Ask: "Create a campaign 'Demo' with two steps, add <lead-address>, start it and show the metrics."
4. Check the viewer at `https://<api-domain>/viewer/`.

## Known gaps

- No OAuth for MCP clients; Claude Desktop needs a local bridge for header auth.
- The tool list is readable without a key.
- Stretch tools (`generate_email_copy`, `analyze_replies`, `recommend_send_time`) are not built.
