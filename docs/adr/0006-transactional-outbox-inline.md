# ADR 0006 — Transactional outbox written inline, no dispatcher yet

**Status:** accepted (Step 2)

## Context

Domain events (`InboundReceived`, `ReplyMatched`, `ReplyClassified`) must not be lost if the process dies between saving state and publishing. A separate outbox publisher process is the textbook answer, but there is no consumer yet.

## Decision

One poll cycle runs `poll → match → classify → persist` in a single database transaction and writes each event as a row in `messaging__outbox_events` in that same transaction. Event payloads follow the JSON Schemas in `contracts/events/<event>/v1.json`. No dispatcher or relay exists until the first consumer (the campaign pause handler) arrives in Step 3.

## Consequences

- At-least-once semantics are available the moment a consumer appears; consumers must be idempotent.
- No dead code for a publisher nobody reads from.
- Event evolution is by version: a `v2.json` next to `v1.json`, handlers accept both.
