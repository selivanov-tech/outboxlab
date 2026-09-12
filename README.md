# OutboxLab

A cold-email outreach engine built as a proof-of-work: clean DDD / hexagonal architecture on a **Postgres-only operational stack** (no Redis, no extra brokers), with an LLM behind a port, not in the core.

**Status: Step 2 of 7 — the real email loop.** Send an email through the Gmail API, poll the inbox, match the reply to the original message, classify its intent, and record events in a transactional outbox. Campaign automation (auto-pause, suppression, send caps) and the MCP server are the next steps — see Roadmap.

## What works today

```
POST /send-test-email ──▶ Gmail API send ──▶ outbound_messages (rfc822 Message-ID stored)
                                                     │
worker: poll inbox ──▶ Gmail API receiver ──▶ match reply by In-Reply-To / References (subject "Re:" fallback)
                                                     │
                                         strip quoted text ──▶ intent classifier ──▶ inbound_messages + outbox events
                                                                 (deterministic rules, optional LLM adapter)
```

- **Send** — `POST /send-test-email` sends through the Gmail API and stores the outbound message with its RFC 822 `Message-ID`.
- **Receive** — a worker process polls the mailbox with a sync cursor, skips the mailbox's own sent mail, and turns raw MIME into a `FetchedMessage`.
- **Match** — a reply is linked to the outbound message by `In-Reply-To` / `References`; a normalised subject match is the fallback.
- **Classify** — intent is one of `positive · negative · ooo · unsubscribe · unclear`. An LLM classifier (Anthropic or OpenAI, chosen by `LLM_PROVIDER`) is a pluggable adapter behind the same port. It is on by default (`LLM_ENABLED=true`) but only activates when the chosen provider's key is set, and it falls back to the deterministic rules on any API error — so a keyless environment (CI, bare demo) stays fully offline. Classification reads the **de-quoted** body, not the snippet, so quoted history does not trigger false positives.
- **Record** — `inbound_received`, `reply_matched`, `reply_classified` events are written to an outbox table in the same transaction; the JSON Schemas live in `contracts/events/`. There is no dispatcher yet — consumers arrive with Step 3.
- **Inspect** — `GET /debug/state` shows workspace / outbound / inbound counts, the mailbox sync cursor, intent counts and the last outbox events; `GET /health`, `GET /version`, `GET /workspaces/me`. The messaging and debug routes are mounted only when `APP_ENV != production`.

## Architecture

Bounded contexts under `apps/api/app/contexts/`, each with `domain / application / infrastructure / presentation`:

| Context | Owns |
|---|---|
| `identity` | workspaces (the tenant registry; the one table deliberately outside RLS) |
| `mailbox` | the connected Gmail mailbox and its sync cursor |
| `messaging` | outbound / inbound messages, reply matching, intent, outbox events |
| `campaign` | table stub only — the state machine arrives in Step 3 |

Rules the code follows:

- **Domain and application depend on ports only.** `EmailSenderPort`, `EmailReceiverPort`, `IntentClassifierPort`, `OutboxEventWriterPort` and the repositories are `Protocol`s; Gmail, the LLM SDKs and SQLAlchemy live in `infrastructure/`.
- **Tenant isolation in the database.** Every tenant table has row-level security keyed by a per-session workspace GUC; tests run as the non-superuser `outboxlab_app` role so the policies are actually exercised.
- **Postgres is the whole ops stack.** Today that means the transactional outbox table; queues, locks and rate limits (Step 3+) will use `SELECT … FOR UPDATE SKIP LOCKED` and advisory locks. No Redis.
- **LLM is optional.** If the key is missing or `LLM_ENABLED=false`, the deterministic classifier answers alone. The demo never depends on a vendor.
- **Every table is prefixed with its context** (`identity__workspaces`, `messaging__inbound_messages`, …) so ownership is visible from the table name.

## Stack

- API: FastAPI (Python 3.14, uv, SQLAlchemy 2.0 async, Pydantic v2), Alembic migrations.
- Worker: Python Gmail poller in the same project (`apps/api/app/entrypoints/worker.py`, run as `python -m app.entrypoints.worker`); own process + own fly app, same image. Go sender extraction is Step 5.
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
docs/            reserved for ADRs (empty so far)
```

## Roadmap

1. ~~Step 0 — local dev stack, Fly deploy path~~
2. ~~Step 1 — walking skeleton: identity context, workspaces, CI, live URL~~
3. ~~Step 2 — real email loop: Gmail send, inbox polling, reply matching, intent classification, outbox~~
4. Step 3 — campaign state machine: a classified reply pauses the lead and cancels future sends; bounce as a first-class signal feeding suppression; per-mailbox daily send caps.
5. Step 4 — hardening, demo, README v2.
6. Step 5 — Go sender extraction behind the same port.
7. Step 6 — MCP server over the API (OpenAPI-as-MCP).
8. Step 7 — observability.

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
- `GET /debug/state` — DB ping, counts, mailbox sync cursor, intents, last outbox events (non-production only)
- `POST /send-test-email` — send one email through the connected Gmail mailbox; needs `X-Workspace-Id` (non-production only)

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
