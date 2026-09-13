# Scale and trade-offs

What the current design deliberately optimises for, what would break first as load grows, and what would move out next. Companion to the [overview](overview.md) and [infrastructure](infrastructure.md) notes.

## Why Postgres is the whole operational stack

The job queue, the per-mailbox lock, the daily cap, the transactional outbox, the processed-events set and the suppression list are all tables and SQL ([ADR 0001](../adr/0001-postgres-only-operational-stack.md)).

- **One transaction boundary.** A lead's state, its next send job, its outbox event and its suppression row commit together. There is no "wrote the row, lost the message" failure mode to design around.
- **Latency budget.** Cold-email sending tolerates seconds of delay; the queue and the consumer are polled every 15–20 seconds.
- **Fewer moving parts.** One managed database instead of a database plus Redis plus a broker, each with its own failure modes, secrets and backups.

**Signals that would justify moving something out** — measured, not guessed:

| Signal | Where to look | What would move |
|---|---|---|
| Queue latency grows | `send_job_latency_seconds` percentiles; pending jobs with `scheduled_at` in the past | more senders first; then the queue to a broker |
| Lock contention | busy deferrals (`last_error = 'mailbox busy'`), `pg_locks` waits | per-mailbox sender affinity instead of advisory locks |
| Connection pool saturation | pool wait time, Postgres `max_connections` | a connection pooler; then fewer polling loops |
| Outbox table growth | row count and index size of `messaging__outbox_events` | pruning processed events; then `LISTEN/NOTIFY` or a broker for dispatch |

## Why fly.io

- A public URL from the first step, deploys gated by CI, and migrations in a release command that fails the deploy instead of the traffic ([ADR 0010](../adr/0010-fly-deploy-with-release-migrations.md)).
- Separate apps per process type (API, worker) from one image, machines that stop when idle, managed Prometheus scraping via `[metrics]`.
- Everything runs in plain containers, so moving to Kubernetes later (parked) is a packaging change, not a code change.

## What breaks first at scale

1. **One worker, one workspace.** The worker serves `MAILBOX_WORKSPACE_ID`, and one Gmail refresh token lives in secrets. Many tenants need encrypted per-mailbox credentials and a worker that iterates mailboxes, each in its own workspace session (parked, with a design in the plan).
2. **Gmail quotas and deliverability.** Provider limits and reputation, not CPU, cap volume: about 20 sends per mailbox per day is the product constraint. Volume grows by adding domains and mailboxes, with warm-up and health scoring (parked).
3. **Polling.** One `history.list` per mailbox per tick is fine for one mailbox; for thousands it needs push notifications or sharded polling.
4. **Send inside the job transaction.** The provider call happens inside a database transaction that holds a row lock and an advisory lock. At high volume that holds connections for the length of an HTTP call; the fix is a claim → send outside the transaction → record result split, with idempotency on the provider side.
5. **At-least-once sending.** A lease that expires during a slow send, or a lost commit, can send twice ([ADR 0014](../adr/0014-send-job-queue-contract.md)). Fine for a demo, visible at volume.
6. **Row-level security with a superuser runtime role.** Policies exist and are tested under a non-superuser role, but the runtime role must be a non-superuser before real multi-tenancy. Until then the queue and consumer filter by workspace explicitly.
7. **Single-process metrics.** Counters are per process ([ADR 0020](../adr/0020-prometheus-metrics.md)); several processes per machine need multiprocess mode.

## Next extraction candidates

1. **Sending, all the way.** Step 5 moved the claim loop to Go ([ADR 0018](../adr/0018-go-sender-claims-and-hands-off.md)). The next move is calling the provider from Go. It has to take the send guards (suppression, mailbox lock, daily cap) and the outbound-message record with it, and it forces the "send outside the transaction" split above.
2. **Reply handling.** Polling, matching and classification form a clear pipeline with one output event (`ReplyClassified` v2). It can run as its own service against the same contract, and the LLM calls make it the natural place for separate scaling and cost control.
3. **Event dispatch.** The processed-events consumer is already transport-agnostic behind a port. Replacing polling of the outbox with `LISTEN/NOTIFY`, or a relay to a broker, changes one adapter per consumer.

Each move keeps the same rule: contexts talk through versioned contracts ([`contracts/`](../../contracts/)), so extraction is an infrastructure change with known risks — data ownership, backfill, retries, idempotency — not a rewrite.
