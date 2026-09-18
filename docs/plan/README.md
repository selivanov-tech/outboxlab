# The 7-step plan

OutboxLab is built in seven short steps. The rule is **critical path first**: every step must strengthen one end-to-end scenario before anything else is added.

> one Gmail mailbox → one campaign → one lead → one sent email → one reply → one classified intent → one paused lead

Anything that does not strengthen that path goes to the [parking lot](#parking-lot).

## Two phases

- **Phase 1 (Steps 0–4): a stable demo.** Remove external risks early, deploy a walking skeleton, build the real email loop, add the campaign state machine, then harden and document.
- **Phase 2 (Steps 5–7): follow-up momentum.** Extract the sender into Go, expose the API as an MCP server, add observability and a second README.

## Steps

| Step | Page | Success signal | Status |
|---|---|---|---|
| 0 | [Local dev stack and deploy path](step-0-local-dev-stack.md) | deploy path, Neon, Gmail OAuth, repo and secrets ready before domain code | done |
| 1 | [Walking skeleton deployed](step-1-walking-skeleton.md) | public fly URL answers `200`, Neon migrations green, seed workspace visible via API | done — [PR #1](https://github.com/selivanov-tech/outboxlab/pull/1) |
| 2 | [Real email loop](step-2-real-email-loop.md) | send an email → reply → poller catches it → intent in DB / API | code merged — [PR #2](https://github.com/selivanov-tech/outboxlab/pull/2); live Gmail end-to-end run still pending |
| 3 | [Campaign state machine](step-3-campaign-state-machine.md) | a classified reply puts the lead in `PAUSED`, future sends are cancelled | code merged — [PR #4](https://github.com/selivanov-tech/outboxlab/pull/4), [PR #10](https://github.com/selivanov-tech/outboxlab/pull/10); live Gmail run pending |
| 4 | [Hardening and demo](step-4-hardening-and-demo.md) | live demo works, README v1 ready | code merged — [PR #6](https://github.com/selivanov-tech/outboxlab/pull/6); demo video and live run pending |
| 5 | [Go sender extraction](step-5-go-sender-extraction.md) | sender implementation can be switched without touching campaign / reply domain logic | code merged — [PR #7](https://github.com/selivanov-tech/outboxlab/pull/7); live switch with real email pending |
| 6 | [MCP server](step-6-mcp-server.md) | the API is usable from Claude Desktop / Claude Code through MCP | code merged — [PR #8](https://github.com/selivanov-tech/outboxlab/pull/8); recorded demo pending |
| 7 | [Observability and README v2](step-7-observability.md) | metrics endpoint, README v2, architecture write-up | code merged — [PR #9](https://github.com/selivanov-tech/outboxlab/pull/9); dashboards optional |
| 8 | [Web console](step-8-web-console.md) | an operator creates a campaign, adds leads, starts it and watches a lead pause, all in the browser | PR open; fly deploy of the console pending |

Each step ships as one pull request titled `Step N: …`. The PR description links back to the step page, so the page is the place to read what the step was for.

## Current status (2026-09-18)

**In `main` and deployed:** Steps 0–7. The API runs on fly.io with migrations up to `0006`; `/health`, `/version`, `/metrics`, `/mcp/` and the legacy `/viewer/` answer. In production the API accepts only workspace API keys.

**Built, in review:** Step 8, the web console (`apps/web`), with CI green.

**Not verified live yet.** Everything below needs real Gmail credentials and is done by hand; until then these paths are covered by tests with fake Gmail and LLM adapters only:

- the send → reply → classify → pause loop against a real mailbox (the success signal of Steps 2 and 3);
- bounce detection on a real delivery-status notification (tested on fixtures shaped like Gmail's);
- the LLM classifier against a real provider key (production currently runs the deterministic rules).

**Deployed by hand, not by CI:** the worker (`make deploy-worker`; without it nothing is sent or received in production), the web console (`make deploy-web`), and the optional Go sender, which has no production path yet because its internal route is disabled in production.

**Next, in order:** merge Step 8 → deploy the web console → remove `/viewer/` from the API → connect a mailbox in production (worker secrets, `seed`) → first live campaign run → demo recordings (console, MCP).

## Cut list and degrade paths

**Not cut before the demo:** real Gmail send, reply detection, reply → classified intent → lead paused, a live URL, README v1.

**Can be degraded if time runs out:**

- LLM classifier → deterministic fallback.
- UI create flow → API / script plus a read-only state viewer.
- Full tenant-isolation test suite → one RLS smoke test.
- OAuth consent UI → manual refresh-token flow.
- 3-step sequence → one immediate step plus one scheduled step.
- Go sender → Python worker first, Go in Step 5.

## Parking lot

Known and useful, but not on the critical path:

- Billing (Stripe subscriptions, mailbox quotas).
- Kind + Helm local Kubernetes.
- Custom domain for the deployed app.
- Full auth: users, memberships, sessions, API key management and rotation. Step 4 added only a minimal workspace API key ([ADR 0017](../adr/0017-workspace-api-keys.md)).
- Removing the single-tenant `MAILBOX_WORKSPACE_ID`. It needs two things together: an OAuth web flow with per-mailbox refresh tokens stored encrypted in the database, and a worker that lists mailboxes from the database and polls each one in its own workspace session. The foundation (RLS per workspace, a tenant registry outside RLS, per-mailbox poll handler, provider-neutral ports) is already in place.
- Encrypted-at-rest mailbox credentials.
- CSV lead upload and a sequence builder UI.
- Bounce *classification*, a dead-letter queue and full DSN recovery. Bounce *as a signal* (mark the address dead, feed suppression) is pulled into Step 3.
- Domain health checker (SPF / DKIM / DMARC).
- Seed-inbox network and warmup loop.
- Error tracking and Grafana dashboards as required artifacts.
- Full re-sync when the Gmail history cursor has expired (today it logs a warning).
