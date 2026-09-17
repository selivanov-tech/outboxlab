# Step 8 — Web console

[← Back to the plan](README.md)

**Status: built, PR open.** The original plan had seven steps; this one came after them, when the read-only viewer stopped being enough. Deploying the console to fly.io is manual (`make deploy-web`).

## Goal

One place in the browser to run the whole demo path: connect a workspace, write a campaign, add leads, start sending, and watch each lead move through the sequence until a reply pauses it.

## Success signal

With the local stack up, an operator opens the web domain, connects, creates a two-step campaign, adds a lead and starts it; when the lead replies, the lead's route on the campaign page changes from "step 1 sent, step 2 next" to "step 2 cancelled" with a "Replied" stamp, without a page reload.

## Decisions

See [ADR 0021](../adr/0021-nextjs-web-console.md): Next.js App Router, Feature-Sliced Design, backend-for-frontend with the API key in an HttpOnly cookie, typed client generated from the exported OpenAPI contract, timer-driven `router.refresh()` instead of a client data layer, separate fly app deployed by hand.

## What was built

**`apps/web`** (Next.js 16, React 19, TypeScript, pnpm)

- `/connect` — paste an API key (or a workspace id for a local API); the key is checked against `GET /workspaces/me` before it becomes the session. `/disconnect` clears it.
- `/campaigns` — every campaign with its status and one bar of all leads split by state.
- `/campaigns/new` — name plus an ordered list of steps (subject, email, wait time with a unit); saved as a draft. A refused form keeps what was typed.
- `/campaigns/{id}` — metrics (contacted, replied, bounced, finished), the sequence, the add-leads form, the start button for a draft, and the lead table. Each lead row shows its **route**: one stop per step (sent, next with its send time, waiting, cancelled) and a stamp when the route ended (replied with the intent, unsubscribed, bounced, suppressed, send failed, complete).
- `/mailbox` — the connected mailbox, today's sends against the daily cap (UTC day), suppressed addresses.
- `/activity` — inbox sync state, message and job counters, the latest outbox events.
- Pages refresh themselves every 5 seconds while the tab is visible. All times are shown in UTC, the clock the send cap uses.
- Layers: `shared` (API client, session, formatting, UI atoms) → `entities` (campaign, mailbox, workspace) → `features` (connect, create campaign, add leads, start campaign, live refresh) → `app` (routes). Pure logic (credential parsing, lead route, lead counts, form parsing, email list parsing, formatting) has unit tests.

**API**

- `contracts/openapi/api-v1.json`, exported from the production app by `python -m app.entrypoints.export_openapi` (`make openapi`); a unit test fails when it is stale.
- `/debug/state` has a response model (same JSON as before).

**Infra**

- `web` compose service (source bind-mounted, dependencies baked into the image), Caddy site on `WEB_DOMAIN`, `WEB_DOMAIN` back in `.env.example` and the Makefile.
- `infra/prod/web/Dockerfile` (standalone output), `infra/prod/fly/web.fly.toml`, `make deploy-web`, a root `.dockerignore`.
- CI job `web`: generated types match the contract, eslint, prettier, tsc, vitest, build. `deploy-api` waits for it.

## Not built

Editing or deleting a campaign, pausing or resuming one (the API has no such routes), CSV import, lead search and paging, users and roles, light/dark themes, end-to-end browser tests.

## Left to do by hand

- Create the fly app, set `OUTBOXLAB_API_URL`, run `make deploy-web`.
- After the console is live: remove `/viewer` from the API (ADR 0016 is superseded).
