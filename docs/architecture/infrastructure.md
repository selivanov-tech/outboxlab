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
| Domain events between contexts | outbox table written in the same transaction; consumer claims with `SKIP LOCKED` and a processed-events set | built (Steps 2–3) |
| Job queue for sends | `campaign__send_jobs` claimed with `SELECT … FOR UPDATE SKIP LOCKED` and a lease | built (Step 3) |
| Rate limit per mailbox | advisory transaction lock per mailbox plus a `count(*)` daily cap per UTC day | built (Step 3) |
| Suppression list | `messaging__suppressions`, fed by bounces and unsubscribes | built (Step 3) |
| Cache | in-process LRU or materialized views, if ever needed | not needed yet |
| Pub / sub between processes | `LISTEN` / `NOTIFY`, if ever needed | not needed yet |

### Job queue shape (Step 3)

Contract and outcomes: [ADR 0014](../adr/0014-send-job-queue-contract.md). Payload: [`contracts/jobs/send_job/v1.json`](../../contracts/jobs/send_job/v1.json).

```sql
CREATE TABLE campaign__send_jobs (
    id                   UUID PRIMARY KEY,
    workspace_id         UUID NOT NULL,
    mailbox_id           UUID NOT NULL,
    lead_id              UUID NOT NULL,
    step_id              UUID NOT NULL,
    payload              JSONB NOT NULL,
    scheduled_at         TIMESTAMPTZ NOT NULL,
    status               VARCHAR(16) NOT NULL,   -- pending / running / done / failed / cancelled
    attempts             INT NOT NULL,
    locked_at            TIMESTAMPTZ,
    locked_by            VARCHAR(128),
    last_error           TEXT,
    outbound_message_id  UUID,                   -- set when sent; links a reply back to the lead
    created_at           TIMESTAMPTZ NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_send_jobs_pending ON campaign__send_jobs (scheduled_at) WHERE status = 'pending';
CREATE INDEX ix_send_jobs_running ON campaign__send_jobs (locked_at) WHERE status = 'running';
```

```sql
-- The Python worker (Step 3) and the Go sender (Step 5) share this contract.
-- :moment is the caller's clock; :lease_expired_before = :moment - 5 minutes.
UPDATE campaign__send_jobs
SET status = 'running', locked_at = :moment, locked_by = :worker_id,
    attempts = attempts + 1, updated_at = :moment
WHERE id IN (
    SELECT id FROM campaign__send_jobs
    WHERE workspace_id = :workspace_id
      AND ((status = 'pending' AND scheduled_at <= :moment)
        OR (status = 'running' AND locked_at < :lease_expired_before))
    ORDER BY scheduled_at
    LIMIT :limit
    FOR UPDATE SKIP LOCKED
)
RETURNING id, workspace_id, mailbox_id, lead_id, payload, attempts, scheduled_at;
```

### Rate limiter shape (Step 3)

Inside the send transaction, after the suppression check ([ADR 0015](../adr/0015-sending-guards-in-messaging.md)):

```sql
-- one sender per mailbox at a time; held until the transaction ends
SELECT pg_try_advisory_xact_lock(hashtext(:mailbox_id));
-- false → busy: the job goes back to pending in a few seconds

-- daily cap, UTC calendar day
SELECT count(*) FROM messaging__outbound_messages
WHERE mailbox_id = :mailbox_id
  AND provider_message_id IS NOT NULL
  AND created_at >= :start_of_utc_day;
-- >= mailbox__mailboxes.daily_send_cap → capped: pending again at the next UTC midnight
```

### Outbox consumer shape (Step 3)

[ADR 0013](../adr/0013-outbox-consumer-processed-events.md):

```sql
SELECT e.id, e.workspace_id, e.payload
FROM messaging__outbox_events e
WHERE e.workspace_id = :workspace_id
  AND e.event_type = 'ReplyClassified'
  AND NOT EXISTS (SELECT 1 FROM campaign__processed_events p WHERE p.event_id = e.id)
ORDER BY e.created_at, e.id
LIMIT :limit
FOR UPDATE OF e SKIP LOCKED;
-- stop the lead, cancel its pending jobs, INSERT INTO campaign__processed_events — one transaction
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
| Worker (Gmail poller, reply consumer, send-job drain) | `outboxlab-worker` | same image, `python -m app.entrypoints.worker`; deployed by hand with `make deploy-worker`; needs its own secrets |
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

- Pattern: `{service}.{project}.{env}.<your-domain>`, for example `api.<project>.<env>.<your-domain>` → `127.0.0.1` for the local environment.
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
