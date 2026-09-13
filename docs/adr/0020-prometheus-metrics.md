# ADR 0020 — Prometheus metrics recorded at the composition roots

**Status:** accepted (Step 7)

## Context

Step 7 needs counters and a latency histogram for the critical path (sends, classified replies, send failures, paused leads, queue latency) and basic HTTP metrics for the API. The work happens in different processes: the worker sends, polls and dispatches; the API processes jobs claimed by the Go sender and serves HTTP. Prometheus counters live per process. Application and domain code must stay free of infrastructure imports.

## Decision

- **Handlers return results; composition roots record them.**
  - `PollInboxHandler` returns the intents it classified.
  - `ProcessClaimedSendJobHandler` returns the job outcome; the claimed job carries its scheduled time.
  - `HandleClassifiedRepliesHandler` returns the stopped leads.
  - The worker entrypoint and the internal process route turn those results into metrics. There is no metrics port, and `prometheus_client` is imported only by shared infrastructure, shared presentation, the campaign infrastructure mapping and the worker entrypoint.
- **Business metrics** (`app/shared/infrastructure/metrics.py`):

  | Metric | Labels | Recorded when |
  |---|---|---|
  | `emails_sent_total` | — | a send job's email is accepted by the provider |
  | `send_job_latency_seconds` (histogram, 1 s … 1 h) | — | same moment: accepted time minus the job's scheduled time |
  | `send_failures_total` | `reason`: `retrying`, `failed`, `suppressed` | a send job does not send; deferrals for a busy or capped mailbox are not failures |
  | `reply_classified_total` | `intent` | a matched reply gets an intent, `bounce` included |
  | `lead_paused_total` | `reason`: `replied`, `unsubscribed` | the reply consumer pauses a lead; a bounced lead fails and is counted as a `bounce` intent instead |

- **HTTP metrics** (`app/shared/presentation/http_metrics.py`, a plain ASGI middleware, the outermost one): `http_requests_total{method, route, status}` and `http_request_duration_seconds{route}`. `route` is the matched route template (`/campaigns/{campaign_id}`), the mount path for mounted apps (`/viewer`, `/mcp`), or `unmatched`. It is never the raw path, so no ids and no unbounded label values. Requests to `/metrics` are not counted.
- **Exposure.**
  - The API serves `GET /metrics` in **every environment, without auth**. That is acceptable because it carries only counters, histograms and route templates: no workspace ids, addresses or message content.
  - The worker starts a separate metrics server when `WORKER_METRICS_PORT` is set. Compose and `worker.fly.toml` set it to `9091`, and fly's `[metrics]` section lets fly's managed Prometheus scrape the worker once it is deployed.
- **Go sender:** structured JSON logs (job, lead, step, attempt, outcome, queue latency) are its signal for now.
- **Parked:** Grafana dashboards, tracing, alerting, error tracking, gauges computed from the database at scrape time.

## Consequences

- The same send is counted by whichever process processed it: the worker with `SENDER_IMPL=python`, the API with `SENDER_IMPL=go`. A dashboard sums both jobs.
- Counters reset when a process restarts; `rate()` / `increase()` handle that.
- A multi-process server (several uvicorn workers in one machine) would need the Prometheus multiprocess mode; today each machine runs one process.
