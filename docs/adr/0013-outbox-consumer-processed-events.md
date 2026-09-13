# ADR 0013 — Outbox consumer: dispatcher in the worker, processed-events set

**Status:** accepted (Step 3; refines [ADR 0006](0006-transactional-outbox-inline.md))

## Context

Step 2 wrote `InboundReceived`, `ReplyMatched` and `ReplyClassified` rows to `messaging__outbox_events` with no reader. Step 3 needs the first consumer: a classified reply must stop the lead in the campaign context and cancel its future sends. The consumer lives in another bounded context, must survive a crash at any point, and must never act twice on one event.

## Decision

- The dispatcher is a step of the worker tick — poll inbox → dispatch classified replies → drain send jobs — not a separate process.
- The campaign context reads events through its own port, `ClassifiedReplyFeedPort`. The adapter in `campaign/infrastructure/messaging/` is the only code outside messaging that knows the outbox table.
- **Claim:** `ReplyClassified` rows for the worker's workspace that have no row in `campaign__processed_events`, ordered by `created_at, id`, locked with `FOR UPDATE … SKIP LOCKED`. Stopping the lead, cancelling its pending jobs and inserting the processed row happen in one transaction.
- **A processed-events set, not an offset.** An event that commits late with an earlier `created_at` is still picked up; an offset would skip it.
- The handler is idempotent on its own as well: stopping a lead that is already paused or failed changes nothing.
- **Versioning:** a payload carries `event_version`; a missing field means v1. `ReplyClassified` v2 adds `matched_outbound_id` and the `bounce` intent. v1 events are acknowledged without changes — they can only belong to test emails sent before campaigns existed.
- Campaign-side events (`LeadPaused`, `LeadCompleted`, …) are not written yet. Nothing consumes them, and the lead row is the record. They arrive with their first consumer (ADR 0012).

## Consequences

- At-least-once delivery with a single effect per consumer, using only Postgres.
- Each consumer owns its processed-events table in its own context; a second consumer adds its own table.
- Dispatch latency equals the worker poll interval (seconds).
- The outbox table keeps growing; pruning processed events is a later concern.
