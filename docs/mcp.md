# MCP access

The OutboxLab API is also an MCP server. An agent — Claude Code, Claude Desktop, or any MCP client — can create a campaign, add leads, start it and read its metrics with the same workspace API key the HTTP API uses.

- **Endpoint:** `https://<api-domain>/mcp/` (streamable HTTP; keep the trailing slash).
- **Auth:** `Authorization: Bearer <api-key>`. Get a key with `make api-key` locally, or with `python -m app.entrypoints.issue_api_key` where `DATABASE_URL` and `MAILBOX_WORKSPACE_ID` are set.
- **How it works:** the tools are generated from the API's OpenAPI document. Each tool call runs the matching HTTP route inside the API process, with your key, so the same checks and the same errors apply. Decision record: [ADR 0019](adr/0019-openapi-as-mcp.md).

## Tools

| Tool | Route | What it does |
|---|---|---|
| `create_campaign` | `POST /campaigns` | create a draft campaign with ordered steps (`subject`, `body`, `delay_seconds`), sent from the workspace mailbox |
| `add_leads_to_campaign` | `POST /campaigns/{campaign_id}/leads` | add lead addresses; scheduled at once if the campaign is already active |
| `start_campaign` | `POST /campaigns/{campaign_id}/start` | schedule the first step for every pending lead; calling it again changes nothing |
| `list_campaigns` | `GET /campaigns` | campaigns with lead counts by state |
| `get_campaign` | `GET /campaigns/{campaign_id}` | steps and every lead's state, stop reason, reply intent and next send time |
| `get_campaign_metrics` | `GET /campaigns/{campaign_id}/metrics` | leads, contacted, emails sent, replies by intent, bounces, reply rate, bounce rate |
| `list_mailboxes` | `GET /mailboxes` | connected mailboxes with the daily cap, sent today, remaining today, suppressed addresses |

Errors come back as tool errors with the API's message:

| Status | Meaning |
|---|---|
| `401` | missing, wrong or revoked API key |
| `404` | campaign not found in your workspace |
| `409` | no mailbox connected to the workspace |
| `422` | invalid input, or starting a campaign that has no leads |

Health, version, debug, viewer, test-email and internal routes are not tools.

## Claude Code

```bash
claude mcp add --transport http outboxlab https://<api-domain>/mcp/ --header "Authorization: Bearer <api-key>"
```

Or commit a project `.mcp.json` that reads the key from your environment:

```json
{
  "mcpServers": {
    "outboxlab": {
      "type": "http",
      "url": "https://<api-domain>/mcp/",
      "headers": { "Authorization": "Bearer ${OUTBOXLAB_API_KEY}" }
    }
  }
}
```

## Claude Desktop

Custom connectors in Claude Desktop expect OAuth. With an API key, one option is a local bridge such as `mcp-remote` in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "outboxlab": {
      "command": "npx",
      "args": ["mcp-remote", "https://<api-domain>/mcp/", "--header", "Authorization:${OUTBOXLAB_AUTH}"],
      "env": { "OUTBOXLAB_AUTH": "Bearer <api-key>" }
    }
  }
}
```

## Example session

> Create a campaign "Q3 outreach" with two steps: "Quick question" now and "Following up" after one day. Add ada@example.com and grace@example.com, start it, then show me the metrics.

The agent calls `create_campaign`, `add_leads_to_campaign`, `start_campaign` and `get_campaign_metrics`. The same campaign appears in the viewer at `https://<api-domain>/viewer/`.

## Notes

- The tool list is readable without a key; every tool call needs one.
- Real emails are sent only while the worker (or the Go sender) runs for that workspace.
