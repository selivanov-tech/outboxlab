# ADR 0009 — Provider-neutral names in domain and ports

**Status:** accepted (Step 2 refactor)

## Context

The first version leaked Gmail vocabulary (`gmail_message_id`, `gmail_thread_id`, `history_id`) into domain entities, ports, database columns and event payloads.

## Decision

Domain, ports, columns and events use neutral names: `provider_message_id`, `provider_thread_id`, `sync_cursor`. Vendor specifics (`historyId`, `threadId`, labels) live only inside `infrastructure/gmail/`. Inbound filtering by label is the adapter's job; the handler only de-duplicates.

There is **no** provider discriminator (no `mailbox.provider` column, no adapter factory) on the email side. The ports are already the seam; a selector with a single value `gmail` would be dead code. The LLM side does have a selector because a second provider exists (ADR 0005).

## Consequences

- A second mail provider is a new adapter pair behind the same ports; no data migration.
- The rule generalises: add a discriminator when the second implementation exists, not before.
