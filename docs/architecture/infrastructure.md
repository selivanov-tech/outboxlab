# Infrastructure

## Database: Neon (managed Postgres) in production, compose Postgres locally

- **Production** runs on Neon. The connection string lives only in fly secrets. Migrations use the direct (non-pooler) URL and run in the fly release command.
- **Local development always uses the compose `postgres` service**, never Neon. Postgres 17.
- Neon's database branching is a nice fit for the CI story later (PR → ephemeral branch → migrations → merge); it is not wired up yet.
- asyncpg does not understand libpq's `sslmode` / `channel_binding` query parameters that Neon URLs carry. A shared helper strips them and maps `sslmode` to asyncpg's `ssl=` argument. It must be used by both the app engine and `alembic/env.py`.

## Postgres-only operational stack

No Redis, no extra brokers. See [ADR 0001](../adr/0001-postgres-only-operational-stack.md).

| Need | Solution | Status |
|---|---|---|
| Domain events between contexts | outbox table written in the same transaction | built (Step 2) |
| Job queue for sends | `send_jobs` table claimed with `SELECT … FOR UPDATE SKIP LOCKED` | Step 3 |
| Rate limit per mailbox | advisory lock per mailbox plus a daily counter / cap | Step 3 |
| Cache | in-process LRU or materialized views, if ever needed | not needed yet |
| Pub / sub between processes | `LISTEN` / `NOTIFY`, if ever needed | not needed yet |

### Job queue shape (Step 3)

```sql
CREATE TABLE campaign__send_jobs (
    id            UUID PRIMARY KEY,
    workspace_id  UUID NOT NULL,
    mailbox_id    UUID NOT NULL,
    lead_id       UUID NOT NULL,
    step_id       UUID NOT NULL,
    payload       JSONB NOT NULL,
    scheduled_at  TIMESTAMPTZ NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',   -- pending / running / done / failed
    attempts      INT NOT NULL DEFAULT 0,
    locked_at     TIMESTAMPTZ,
    locked_by     TEXT,
    created_at    TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_send_jobs_pending ON campaign__send_jobs (scheduled_at, status) WHERE status = 'pending';
```

```sql
-- The Python worker (Step 3) and the Go sender (Step 5) share this contract.
UPDATE campaign__send_jobs
SET status = 'running', locked_at = now(), locked_by = $1, attempts = attempts + 1
WHERE id IN (
    SELECT id FROM campaign__send_jobs
    WHERE status = 'pending' AND scheduled_at <= now()
    ORDER BY scheduled_at
    LIMIT 10
    FOR UPDATE SKIP LOCKED
)
RETURNING id, mailbox_id, lead_id, payload;
```

### Rate limiter shape (Step 3)

```sql
-- one worker per mailbox at a time
SELECT pg_try_advisory_xact_lock(hashtext($mailbox_id::text));
-- true  → check the daily counter, increment, send
-- false → skip; another worker is sending from this mailbox
```

### Why no Redis

- Most queue work in this domain tolerates a few seconds of latency; Postgres polling is enough.
- Fewer moving parts in production.
- Transactional consistency between business rows and job rows comes for free — no "wrote to the DB, forgot the queue" class of bugs.
- If load grows an order of magnitude, move the queue or rate limiter out **after** measuring queue latency, lock contention and pool saturation.

## Deploy: fly.io

| Service | fly app | Notes |
|---|---|---|
| API (FastAPI) | `outboxlab-api` | deployed by CI on every push to `main` |
| Worker (Gmail poller) | `outboxlab-worker` | same image, `python -m app.entrypoints.worker`; deployed by hand with `make deploy-worker`; needs its own secrets |
| Web (state viewer) | `outboxlab-web` | static placeholder today |
| Sender (Go) | later | Step 5 |

- Region `iad`. `auto_stop_machines` with `min_machines_running = 0` outside demo weeks.
- Secrets via `fly secrets set`: database URL, API domain, Google OAuth values, LLM key.
- The api `release_command` runs `alembic upgrade head` in a one-off VM before serving machines start, so a broken migration fails the deploy instead of reaching traffic ([ADR 0010](../adr/0010-fly-deploy-with-release-migrations.md)).
- `Settings` has required fields (`DATABASE_URL`, `API_DOMAIN`, `APP_ENV`) that are read at import time by both the app and Alembic. Every environment — local, CI, the fly release command — must set them.

## Local development: Docker Compose

Compose is the daily runtime. The host keeps only account-bound tools (Docker, `fly`, optionally `gh` / `gcloud`); `uv`, `psql` and friends live inside the containers.

Services: `proxy` (Caddy with local HTTPS), `api`, `worker`, `web`, `postgres`.

**Env strategy**

- `.env` for local compose (git-ignored; holds real local domains).
- `.env.example` as the contract, no secrets, committed.
- `fly secrets set` for deployed environments.

**Local domains**

- Pattern: `{service}.{project}.{env}.<your-domain>`, for example `api.<project>.local.<your-domain>` → `127.0.0.1`.
- Google OAuth web redirect URIs need a public top-level domain, so `.test` / `.localhost` do not work for the callback.
- TLS via `mkcert` (`make certs`); hosts entries via `make hosts-add`.
- Domains never appear in tracked files: `make check-leaks` (also a CI job) fails the build if they do.

Kubernetes (Kind + Helm) is a parked follow-up, not part of the critical path.

## References

- Neon docs: https://neon.tech/docs
- `SELECT … FOR UPDATE SKIP LOCKED`: Postgres docs on row-level locking
- fly.io launch docs and `fly.toml` reference: https://fly.io/docs/launch
- Gmail API: https://developers.google.com/gmail/api
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
