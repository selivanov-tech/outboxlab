# Step 7 — Observability and README v2

[← Back to the plan](README.md)

**Status: code merged** — PR_STEP_7. Dashboards and a follow-up recording are optional and manual.

## Goal

Follow-up material: metrics, README v2, an architecture write-up.

## Success signal

Follow-up material is ready: MCP demo, README v2, metrics.

- `/metrics` on the API and on the worker, with the business counters and the latency histogram recorded from real handler results. Unit tests cover the counters, and HTTP labels use route templates.
- README v2 and [scale and trade-offs](../architecture/scale-and-tradeoffs.md) are in the repository.
- The MCP demo recording is manual (Step 6).

## Checklist

- [x] `/metrics` on the FastAPI app; `/metrics` or structured logs on the sender — API `GET /metrics`; the worker exposes metrics on `WORKER_METRICS_PORT`; the Go sender logs structured JSON.
- [x] Counters and histograms: `emails_sent_total`, `reply_classified_total`, `send_failures_total`, `lead_paused_total`, `send_job_latency_seconds`.
- [ ] Grafana dashboard — optional, parked.
- [x] README v2: DDD boundaries, outbox, queue, Go sender extraction, MCP.
- [x] Architecture write-up: why Postgres-only, why fly.io, what breaks at scale, next extraction candidates — [`docs/architecture/scale-and-tradeoffs.md`](../architecture/scale-and-tradeoffs.md).

## Locked decisions (as built)

See [ADR 0020](../adr/0020-prometheus-metrics.md).

1. **Handlers return results; composition roots record metrics.** No metrics port, no Prometheus import in domain or application code.
2. **Where each counter lives.** The worker records what it does: replies classified, leads paused, and sends when `SENDER_IMPL=python`. The API records sends it processes for the Go sender.
3. **HTTP labels are bounded:** route templates, mount paths or `unmatched`; `/metrics` itself is not counted.
4. **`/metrics` is public in every environment.** It carries only counters, histograms and route templates.
5. **No root `ARCHITECTURE.md`.** The write-up lives in `docs/architecture/`, with the other architecture notes.

## What was built

- `app/shared/infrastructure/metrics.py`: the business counters and histogram with small `record_*` functions.
- `app/contexts/campaign/infrastructure/metrics.py`: maps send-job outcomes and stopped leads to those functions.
- `app/shared/presentation/http_metrics.py` (ASGI middleware) and `GET /metrics`.
- `PollInboxHandler` returns a `PollResult` with the classified intents; `ProcessSendJobByIdHandler` returns the job with its outcome.
- The worker records poll, dispatch and drain results and starts a metrics server on `WORKER_METRICS_PORT`. The internal process route records sends made for the Go sender.
- `worker.fly.toml`: `WORKER_METRICS_PORT` and a `[metrics]` section; compose exposes the worker's port inside the network.
- README v2, `docs/architecture/scale-and-tradeoffs.md`, ADR 0020.
- Tests: counters per outcome and reason, latency observation, paused versus bounced leads, intents, HTTP labels for a route template, a mount and an unknown path, the `/metrics` endpoint.

## Changes compared with the plan

- `ARCHITECTURE.md` became `docs/architecture/scale-and-tradeoffs.md`.
- `send_failures_total` counts `retrying`, `failed` and `suppressed`; busy or capped deferrals are not failures.
- A bounced lead is not "paused"; bounces are visible as `reply_classified_total{intent="bounce"}`.

## Look at the metrics locally

```bash
docker compose -f infra/dev/docker-compose.yml --env-file .env exec api curl -s http://127.0.0.1:8000/metrics | grep -E '^(http_requests_total|emails_sent_total)'
docker compose -f infra/dev/docker-compose.yml --env-file .env exec worker curl -s http://127.0.0.1:9091/metrics | grep -E '^(reply_classified_total|lead_paused_total|send_job_latency_seconds_count)'
```

The worker needs a restart after this change to open its metrics port.

## Known gaps

- No dashboards or alerts.
- Go sender metrics are log lines, not a `/metrics` endpoint.
- Counters are per process; several processes per machine would need Prometheus multiprocess mode.
