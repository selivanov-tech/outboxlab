# ADR 0001 — Postgres-only operational stack

**Status:** accepted (Step 0)

## Context

A cold-email engine needs domain events, a send queue, a per-mailbox rate limit and, later, a small cache. The usual answer is Redis plus a broker. This project is small, single-team, and wants the fewest moving parts that still demonstrate the patterns correctly.

## Decision

Postgres is the whole operational stack. Domain events go to an outbox table in the same transaction as the state change. The send queue is a table claimed with `SELECT … FOR UPDATE SKIP LOCKED`. Per-mailbox rate limiting uses an advisory lock plus a counter. Cache, if ever needed, is in-process or a materialized view. No Redis, no message broker.

## Consequences

- Business rows and job rows commit together; there is no "wrote to the DB, forgot the queue" bug class.
- Queue latency is polling latency (seconds), which this domain tolerates.
- Fewer services to run, secure and monitor on fly.io.
- If load grows an order of magnitude, the queue or rate limiter can move out **after** measuring queue latency, lock contention and connection-pool saturation. The ports make that an infrastructure change.
