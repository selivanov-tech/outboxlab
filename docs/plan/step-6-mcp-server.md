# Step 6 — MCP server

[← Back to the plan](README.md)

**Status: planned.**

## Goal

Let an AI agent (Claude Desktop / Claude Code) drive campaign use cases through MCP, with zero domain logic in the MCP layer.

## Decision: OpenAPI-as-MCP first

The default is to expose the FastAPI OpenAPI document as an `openapi`-type MCP server: base URL, OpenAPI URL, and an auth header (`Authorization` or `x-api-key`). This is far less code than hand-written tools and keeps the tool surface in sync with the HTTP API. Hand-written tools stay as a fallback and as an illustration of a control plane.

## Fallback: hand-written tools

If hand-written tools are needed, each one is a thin wrapper over an existing application use case (commands / queries), only marshalling arguments:

- `create_campaign(name, mailbox_ids, steps)`
- `add_leads_to_campaign(campaign_id, leads)`
- `pause_campaign(campaign_id)` / `resume_campaign(campaign_id)`
- `get_campaign_metrics(campaign_id)` → sent, replied, reply intents, bounced, in progress, completed, reply rate, bounce rate
- `list_mailboxes()` → address, provider, status, health (bounce rate, sent today, limit)

## Checklist

- [ ] Auth through a workspace API key checked on every call; it resolves the workspace id and sets it in context.
- [ ] Basic error handling: invalid campaign, mailbox not connected, no leads.
- [ ] Example config for Claude Desktop / Claude Code.
- [ ] Short demo: the agent creates a campaign, adds leads, and reads metrics.

## Stretch

`generate_email_copy`, `analyze_replies` (summary of the last N replies), `recommend_send_time`.

## Success signal

MCP works locally through Claude Desktop / Claude Code; the demo is recorded.
