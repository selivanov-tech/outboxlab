# Step 7 — Observability and README v2

[← Back to the plan](README.md)

**Status: planned.**

## Goal

Follow-up material: metrics, README v2, an architecture write-up.

## Checklist

- [ ] `/metrics` on the FastAPI app; `/metrics` or structured logs on the sender.
- [ ] Counters and histograms: `emails_sent_total`, `reply_classified_total`, `send_failures_total`, `lead_paused_total`, `send_job_latency_seconds`.
- [ ] Grafana dashboard, optional, once `/metrics` works.
- [ ] README v2: DDD boundaries, outbox, queue, Go sender extraction, MCP.
- [ ] `ARCHITECTURE.md`: why Postgres-only, why fly.io, what breaks at scale, next extraction candidates.

## Artifacts

Metrics endpoint / logs, README v2, `ARCHITECTURE.md`, a short update with screenshots or a video.

## Success signal

Follow-up material is ready: MCP demo, README v2, metrics.
