# Step 4 — Hardening and demo

[← Back to the plan](README.md)

**Status: code merged** — [PR #6](https://github.com/selivanov-tech/outboxlab/pull/6). The demo video and the live run on the deployed URL are done by hand.

## Goal

No big features. Stabilise, package, record a short demo, finish README v1.

## Success signal

The live demo works, the video is recorded, the README is ready.

## Checklist

- [x] Minimal read-only state viewer: campaigns, leads, statuses, reply intent — `/viewer/`, served by the API ([ADR 0016](../adr/0016-viewer-served-by-the-api.md)). Creating a campaign stays an API call.
- [x] Smoke-test checklist on the deployed URL: health, database, mailbox, send, reply, pause — `scripts/smoke.sh` and the checklist below.
- [ ] Check cold start and logs on fly.io — manual, after the merge deploys (checklist below).
- [x] Remove obvious demo breakers: hard-coded local URLs, missing env vars, fragile seed data.
- [x] README v1 finalised: demo path, architecture, trade-offs, run instructions. Screenshots are listed below for the manual pass.
- [ ] Demo video (about 3 minutes) — manual.
- [x] Write down what worked, what was intentionally deferred, and the next three tasks — retro below.

## Locked decisions (as built)

1. **Minimal workspace API keys, pulled forward from Step 6** ([ADR 0017](../adr/0017-workspace-api-keys.md)). Without a credential the campaign routes could only run locally. A key `olab_<prefix>_<secret>` resolves the workspace; the prefix and the SHA-256 of the secret are stored (`identity__api_keys`, migration `0006`); `make api-key` prints a key once. In production the key is the only way in and `X-Workspace-Id` is rejected. No key-management routes, no rotation.
2. **Viewer in the API, web placeholder removed** ([ADR 0016](../adr/0016-viewer-served-by-the-api.md)). One HTML file and one JavaScript file at `/viewer/`, same origin, no build. `apps/web`, the `web` compose service, its Dockerfiles, `web.fly.toml` and `WEB_DOMAIN` are gone.
3. **Mounting.** Campaign routes, `/debug/state` (now scoped to the caller's workspace) and `/viewer/` are served in every environment behind the key. `/send-test-email` stays non-production.

## What was built

- Identity: `ApiKey` entity, repository, issue command, resolve query, `python -m app.entrypoints.issue_api_key`; migration `0006`.
- `WorkspaceContextMiddleware` takes a key resolver and a flag for the workspace header; `create_app(settings)` composes the app per environment.
- `/debug/state` needs credentials and counts only the caller's workspace (outbound, inbound, intents, lead states, job statuses, recent events, sync cursor).
- Viewer: campaign list with lead counts, campaign detail with steps and leads (state, stop reason, reply intent, next send, last change), workspace counts and recent events, refresh every 5 seconds.
- Demo helpers: `make smoke-readonly`, `make smoke SMOKE_LEAD_EMAIL=…`, `make demo-reset [CONFIRM=yes]`, `make api-key`; the worker logs its loops, workspace and classifier at start.
- Removed: the web placeholder and `WEB_DOMAIN` (Makefile, Caddy, compose, `.env.example`).
- Tests for keys, middleware, per-environment mounting and the viewer files.

## Changes compared with the plan

- The API key was planned for Step 6. It moved here so the deployed URL can run the demo; Step 6 reuses it for MCP.
- Next.js was dropped. The viewer is a static page in the API, and the placeholder was deleted instead of replaced.
- No screenshots in the repository yet. They are listed for the manual pass.

## Smoke tests

**Local, no email:**

```bash
make smoke-readonly
```

It checks `/health`, `/version`, `/debug/state` (database and sync cursor) and `/campaigns` inside the api container. When `MAILBOX_WORKSPACE_ID` is not in `.env`, pass the workspace id to the script directly:

```bash
docker compose -f infra/dev/docker-compose.yml --env-file .env exec -T -e SMOKE_WORKSPACE_ID=<workspace-id> api bash -s -- readonly http://127.0.0.1:8000 < scripts/smoke.sh
```

**Full run, real email** (worker running, a separate lead mailbox you control):

```bash
make smoke SMOKE_LEAD_EMAIL=<lead-address>
```

It creates a two-step campaign (the second step after 10 minutes), adds the lead, starts it, waits for `sent`, asks you to reply, then waits for `paused` with no send scheduled.

**Deployed URL** (after the merge deploys the API):

1. `GET /health` is `200`; `GET /version` shows the merge commit.
2. The deploy log shows the release command applying migration `0006`.
3. Issue a key once, with `DATABASE_URL` and `MAILBOX_WORKSPACE_ID` set, on a machine of the API app or from a local shell pointed at the production database: `python -m app.entrypoints.issue_api_key`.
4. Read-only smoke from your laptop: `SMOKE_API_KEY=<key> scripts/smoke.sh readonly https://<api-domain>`.
5. `GET /campaigns` without a key is `401`; with `X-Workspace-Id` it is also `401`; `/viewer/` loads and connects with the key.
6. Cold start: with `min_machines_running = 0`, measure the first request after idle (`curl -o /dev/null -s -w '%{time_total}\n' https://<api-domain>/health`). For demo day, set `min_machines_running = 1` in `infra/prod/fly/api.fly.toml` (costs money while it runs).
7. Real sends from production need the worker app deployed with its secrets (`infra/prod/fly/worker.fly.toml`), then `SMOKE_API_KEY=<key> SMOKE_LEAD_EMAIL=<lead-address> scripts/smoke.sh full https://<api-domain>`.

## Demo reset

`make demo-reset` shows how many campaign and message rows `MAILBOX_WORKSPACE_ID` has; `make demo-reset CONFIRM=yes` deletes them in one transaction. The workspace, the mailbox and its sync cursor stay. It refuses to run unless `APP_ENV=local` and `MAILBOX_WORKSPACE_ID` are set in `.env`.

## Screenshots for the manual pass

- The viewer with one campaign: the lead `sent` with a next send time.
- The same view a few seconds after the reply: the lead `paused`, intent `positive`, no next send.
- `GET /debug/state` with the `ReplyClassified` event at the top.

## Retro

**What worked**

- Critical path first: every step ended with a runnable proof, and the Step 3 success signal is an integration test in CI.
- Postgres as the only operational dependency: queue, locks, cap, outbox and suppressions are plain tables and SQL, tested against the real database with the RLS role.
- Ports at the context borders kept each change local: the key gate, the viewer and the send guards did not touch the campaign domain.

**Intentionally deferred**

- Users, memberships and key management; multi-tenant worker; OAuth web flow.
- Bounce classes and mailbox health; follow-ups threaded into the same conversation.
- A create or edit UI; metrics (Step 7).

**Next three tasks**

1. Run the live demo end to end on the deployed URL with the worker deployed, then record the video.
2. Go sender on the frozen job contract (Step 5).
3. Expose the API to MCP clients with the same API key (Step 6).
