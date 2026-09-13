# OutboxLab

A cold-email outreach engine built as a proof-of-work: clean DDD / hexagonal architecture on a **Postgres-only operational stack** (no Redis, no extra brokers), with an LLM behind a port, not in the core.

**Status: Step 3 of 7 — the campaign state machine.** A campaign sends its sequence through a Postgres job queue; a classified reply pauses the lead and cancels its future sends; bounces and unsubscribes feed a suppression list; every mailbox has a daily cap. Hardening and the demo, the Go sender, the MCP server and metrics are the next steps — see Roadmap.

## What works today

```
POST /campaigns → /leads → /start ─▶ campaign__send_jobs (pending, step 1 now, step 2 later)
                                              │
worker: drain ─▶ claim (SKIP LOCKED, lease) ─▶ suppression · mailbox lock · daily cap ─▶ Gmail API send
                                              │
worker: poll ─▶ Gmail API receiver ─▶ match reply (In-Reply-To / References / thread / subject + address)
                                              │
                    delivery failure? ─▶ intent bounce      otherwise ─▶ classifier (rules or LLM)
                                              │
                    inbound_messages + suppressions + outbox event ReplyClassified v2
                                              │
worker: dispatch ─▶ campaign consumer ─▶ lead paused (failed on bounce) + pending jobs cancelled
```

- **Campaigns** — a campaign has ordered steps (`subject`, `body`, `delay_seconds`) and leads. Lead state (`pending → scheduled → sent → done`, or `paused` / `failed`) changes only through the `Campaign` aggregate. `POST /campaigns/{id}/start` is idempotent.
- **Send queue** — jobs live in `campaign__send_jobs` and are claimed with `SELECT … FOR UPDATE SKIP LOCKED` and a 5-minute lease. Each job runs in its own transaction; a send error retries with backoff and fails the lead after three attempts. The payload is frozen in `contracts/jobs/send_job/v1.json` for other sender implementations.
- **Sending guards** — before every send (campaign or test email): the recipient must not be suppressed, the mailbox takes a Postgres advisory lock, and today's sent count (UTC day) must be under the mailbox's `daily_send_cap` (default 20). A capped job waits for the next UTC day.
- **Receive and match** — a worker polls the mailbox with a sync cursor, skips its own sent mail, and links a reply to the outbound message by `In-Reply-To` / `References`, then thread, then a normalised subject from the same address.
- **Bounces and unsubscribes** — the Gmail adapter flags delivery-status notifications; they skip the classifier, get intent `bounce`, suppress the address and fail the lead. An `unsubscribe` reply suppresses the address too.
- **Classify** — intent is one of `positive · negative · ooo · unsubscribe · unclear` (plus `bounce` from the adapter). An LLM classifier (Anthropic or OpenAI, chosen by `LLM_PROVIDER`) sits behind the same port; it only activates when the chosen provider's key is set and falls back to deterministic rules on any error, so a keyless environment stays offline. Classification reads the **de-quoted** body, not the snippet.
- **Outbox and consumer** — `InboundReceived`, `ReplyMatched`, `ReplyClassified` are written to an outbox table in the same transaction (JSON Schemas in `contracts/events/`). The campaign context consumes `ReplyClassified` with a processed-events set: at-least-once delivery, one effect per event.
- **Inspect** — `GET /campaigns`, `GET /campaigns/{id}` (leads with state, stop reason, reply intent, next send time), `GET /debug/state` (counts, sync cursor, intents, lead states, job statuses, last outbox events), `GET /health`, `GET /version`, `GET /workspaces/me`. Campaign, messaging and debug routes are mounted only when `APP_ENV != production`, because the API has no auth yet.

## Demo path (local stack)

1. Seed the workspace and mailbox; wait until `/debug/state` shows a sync cursor.
2. `POST /campaigns` with two steps (the second with a short `delay_seconds`), `POST /campaigns/{id}/leads` with an address you control, `POST /campaigns/{id}/start`.
3. The worker sends step 1; `GET /campaigns/{id}` shows the lead `sent` and its next send time.
4. Reply from the lead mailbox. Within one poll the reply is matched and classified, the lead turns `paused`, and the step-2 job is `cancelled`.

The full runbook with commands is on the [Step 3 page](docs/plan/step-3-campaign-state-machine.md#live-campaign-runbook-manual-real-credentials).

## Trade-offs and what is intentionally not built

- **Postgres is the whole ops stack.** Queue, lock, cap, outbox and suppressions are tables and SQL; latency is the poll interval (seconds). Moving any of them out is an infrastructure change after measuring queue latency and lock contention.
- **At-least-once sending.** A send still in flight after its lease, or a commit that fails after Gmail accepted the message, can be sent twice on retry. Exactly-once would need provider-side idempotency.
- **One worker, one workspace.** The worker serves `MAILBOX_WORKSPACE_ID`; multi-tenant polling and an OAuth web flow are parked.
- **No auth yet.** Write routes are non-production only; workspace API keys come with the MCP step.
- **Not built:** bounce classes and a mailbox health score, follow-ups threaded into the same Gmail conversation, campaign pause / resume, templating, CSV import, a UI (Step 4 adds a read-only viewer), metrics (Step 7).

## Architecture

Bounded contexts under `apps/api/app/contexts/`, each with `domain / application / infrastructure / presentation`:

| Context | Owns |
|---|---|
| `identity` | workspaces (the tenant registry; the one table deliberately outside RLS) |
| `mailbox` | the connected Gmail mailbox and its sync cursor |
| `messaging` | outbound / inbound messages, reply matching, intent, bounce detection, suppressions, sending guards, outbox events |
| `campaign` | campaigns, steps, leads and their state machine; the send-job queue; the reply consumer |

Rules the code follows:

- **Domain and application depend on ports only.** `EmailSenderPort`, `EmailReceiverPort`, `IntentClassifierPort`, `OutboxEventWriterPort` and the repositories are `Protocol`s; Gmail, the LLM SDKs and SQLAlchemy live in `infrastructure/`.
- **Tenant isolation in the database.** Every tenant table has row-level security keyed by a per-session workspace GUC; tests run as the non-superuser `outboxlab_app` role so the policies are actually exercised.
- **Postgres is the whole ops stack.** The transactional outbox, the send-job queue (`SELECT … FOR UPDATE SKIP LOCKED`), an advisory lock per mailbox and a `count(*)` daily cap. No Redis.
- **LLM is optional.** If the key is missing or `LLM_ENABLED=false`, the deterministic classifier answers alone. The demo never depends on a vendor.
- **Every table is prefixed with its context** (`identity__workspaces`, `messaging__inbound_messages`, …) so ownership is visible from the table name.

## Stack

- API: FastAPI (Python 3.14, uv, SQLAlchemy 2.0 async, Pydantic v2), Alembic migrations.
- Worker: Python process in the same project (`apps/api/app/entrypoints/worker.py`, run as `python -m app.entrypoints.worker`) — polls Gmail, dispatches classified replies, drains send jobs; own process + own fly app, same image. Go sender extraction is Step 5.
- Web: a static placeholder page served by Caddy. The Next.js state viewer is Step 4.
- DB: local postgres 17 (dev) / Neon (prod).
- Deploy: fly.io.

## Layout

```
apps/
  api/           FastAPI app, worker entrypoint, Alembic migrations, tests
                 app/contexts/<bc> · app/shared · app/entrypoints (api/worker/seed)
  web/           static placeholder page
contracts/       event JSON Schemas (versioned)
infra/
  dev/           docker-compose + dev Dockerfiles + Caddy proxy
  prod/          prod Dockerfiles + fly.toml
  make/          shared make fragments (deploy.mk)
docs/            plan (one page per step), architecture notes, ADRs
```

## Roadmap

The full plan, one page per step, lives in [`docs/plan/`](docs/plan/README.md). Decisions are recorded in [`docs/adr/`](docs/adr/README.md); the context map and infrastructure notes in [`docs/architecture/`](docs/architecture/overview.md).

1. ~~[Step 0](docs/plan/step-0-local-dev-stack.md) — local dev stack, Fly deploy path~~
2. ~~[Step 1](docs/plan/step-1-walking-skeleton.md) — walking skeleton: identity context, workspaces, CI, live URL~~
3. ~~[Step 2](docs/plan/step-2-real-email-loop.md) — real email loop: Gmail send, inbox polling, reply matching, intent classification, outbox~~
4. ~~[Step 3](docs/plan/step-3-campaign-state-machine.md) — campaign state machine: a classified reply pauses the lead and cancels future sends; bounce as a first-class signal feeding suppression; per-mailbox daily send caps.~~
5. [Step 4](docs/plan/step-4-hardening-and-demo.md) — hardening, demo, README v1.
6. [Step 5](docs/plan/step-5-go-sender-extraction.md) — Go sender extraction behind the same port.
7. [Step 6](docs/plan/step-6-mcp-server.md) — MCP server over the API (OpenAPI-as-MCP).
8. [Step 7](docs/plan/step-7-observability.md) — observability, README v2.

## First-time setup

Prereqs: a Docker engine, `mkcert` (`brew install mkcert nss`), `make`.

> macOS / Apple Silicon: Docker Desktop, OrbStack, or Colima all work. OrbStack is
> the fastest path if you hit networking quirks on ports 80/443 with Docker Desktop.

```bash
make env         # copy .env.example -> .env
# edit .env: set API_DOMAIN, WEB_DOMAIN.
# For the live email loop also set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
# GOOGLE_REFRESH_TOKEN, GMAIL_USER_EMAIL (tests and the API run without them).
make certs       # generate TLS certs for your domains
make hosts-add   # append /etc/hosts entries (sudo)
make up          # start containers
```

`make setup` runs `make env` and prints the next steps — you still need to edit `.env`
before `make certs` so mkcert sees your domains.

Open URLs are printed by `make up` and live only in your `.env`.

After `make up`:

```bash
make migrate     # apply Alembic migrations to local postgres
make seed        # insert the default workspace + mailbox (idempotent; mailbox only if GMAIL_USER_EMAIL is set)
make test        # run unit + integration tests
make lint        # ruff format-check + lint (same as CI)
```

Endpoints (replace with your `API_DOMAIN`):

- `GET /health` — liveness
- `GET /version` — version + git SHA + APP_ENV
- `GET /workspaces/me` — the workspace from the `X-Workspace-Id` header
- `GET /debug/state` — DB ping, counts, mailbox sync cursor, intents, lead states, send-job statuses, last outbox events (non-production only)
- `POST /send-test-email` — send one email through the connected Gmail mailbox; needs `X-Workspace-Id`; 409 for a suppressed recipient, 429 for a busy or capped mailbox (non-production only)
- `POST /campaigns`, `POST /campaigns/{id}/leads`, `POST /campaigns/{id}/start`, `GET /campaigns`, `GET /campaigns/{id}` — campaign API; needs `X-Workspace-Id` (non-production only)

## Daily

```bash
make up          # start
make logs        # tail
make ps          # status
make shell-api   # bash into api
make shell-worker # bash into worker
make shell-db    # psql into postgres
make migrate     # apply pending Alembic migrations
make test        # run pytest
make typecheck   # pyright (api)
make lint        # check format + lint with ruff
make format      # auto-format + autofix with ruff (writes changes)
make ready       # pre-commit gate: leaks + ruff + pyright + tests
make down        # stop
make clean       # stop + drop volumes
```

`make help` lists everything.

## Adding a migration

```bash
# edit ORM models in apps/api/app/contexts/<bc>/infrastructure/db/models.py
make migration name="describe the change"
# review apps/api/alembic/versions/<new_file>.py
make migrate
```

Baseline migration is hand-written (`alembic/versions/0001_baseline.py`) so its
DDL + RLS policies stay reviewable; subsequent migrations use autogenerate.
Tables are named `{bc}__{table}`; the prefix goes into `__tablename__`, the
`ForeignKey` target and the migration. Index and constraint names keep their plain form.

## RLS app role

The migration assumes a non-superuser role `outboxlab_app` exists at the cluster
level. Tests `SET LOCAL ROLE outboxlab_app` to exercise RLS policies as a
non-superuser (FORCE RLS doesn't help under a superuser).

- **Local (compose)**: created automatically by
  `infra/postgres/bootstrap_app_role.sql`, mounted into the postgres image's
  `/docker-entrypoint-initdb.d/`. Runs once on an empty data dir, so re-runs
  need `make clean` first.
- **CI**: a workflow step pipes the same SQL through `psql` before migrations.
- **Prod (Neon)**: run the same SQL once against your Neon DB via the Neon SQL
  editor (or `psql` with the direct URL). Migrations themselves never touch
  roles, so the runtime app role only needs SELECT/INSERT/UPDATE/DELETE on the
  schema — no CREATEROLE required.

## CI

GitHub Actions runs on every PR:

- **api-tests** — Postgres 17 service, app-role bootstrap, migrations, seed, pytest.
- **typecheck** — pyright on api (the worker lives in the api project).
- **lint** — ruff `format --check` + `check` on api (pinned 0.15.15).
- **leak-check** — fails if a tracked file leaks a hostname.

On merge to `main`, the **deploy-api** job ships the api to fly.io. It runs only
after all four checks pass (`needs:`) and inside the `production` environment.

One-time setup: add a fly deploy token as the `FLY_API_TOKEN` secret (repo or
the `production` environment):

```bash
fly tokens create deploy -a outboxlab-api
```

The CI-facing targets (`deploy`, `check-leaks`) live in `infra/make/deploy.mk`
so CI calls them standalone; the dev Makefile includes the same file, so
`make deploy` / `make check-leaks` still work locally.

## Deploy (fly.io)

Merging to `main` auto-deploys the **api** through the CI **deploy-api** job. To deploy by
hand:

```bash
# one-time: bootstrap the app role on Neon (Neon SQL editor or psql).
psql "$NEON_DIRECT_URL" -f infra/postgres/bootstrap_app_role.sql

# one-time: point fly at Neon (direct, non-pooler URL for migrations) and set
# the API domain — Settings requires it, and the release migration builds it.
fly secrets set -a outboxlab-api \
  DATABASE_URL="postgresql+asyncpg://<neon-url>" \
  API_DOMAIN="<your-api-domain>"

# every deploy (wraps fly deploy; see infra/make/deploy.mk)
make deploy
```

The `[deploy] release_command` in `api.fly.toml` runs `alembic upgrade head`
in a one-off VM before serving machines start, so a broken migration fails
the deploy rather than reaching live traffic.

The **worker** is not deployed by CI. `make deploy-worker` ships it as the
separate fly app `outboxlab-worker` from the same image; it needs its own
secrets (`DATABASE_URL`, `API_DOMAIN`, the Google OAuth values, `GMAIL_USER_EMAIL`,
`MAILBOX_WORKSPACE_ID`, optionally the LLM key) — see `infra/prod/fly/worker.fly.toml`.

## Package managers

- Python: `uv` (no pip, no poetry).
- Node: `pnpm` (no npm, no yarn, no bun lockfiles).
