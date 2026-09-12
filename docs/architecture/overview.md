# Architecture overview

OutboxLab is a **modular monolith**: one FastAPI codebase split into bounded contexts that talk to each other only through infrastructure adapters. The goal is not "any context can become a service in a day" but "the cost of extracting one later is known and low": versioned event contracts, side effects through an outbox, and `Sending` as the first extraction candidate.

## Code layout

```
apps/api/app/
  contexts/<bc>/          one folder per bounded context
    domain/               entities, value objects, domain events — zero I/O
    application/          use cases (commands / queries / handlers) and ports (Protocols)
    infrastructure/       adapters: SQLAlchemy models + repositories, Gmail, LLM clients, outbox writer
    presentation/         FastAPI routes for this context
  shared/                 cross-cutting: DB engine, clock, request context, debug/health/version routes
  entrypoints/            process roots that cross context borders: api.py, worker.py, seed.py
  config.py               Settings (pydantic-settings)
contracts/events/         versioned JSON Schemas for outbox events
```

Rules:

- **Domain and application depend on ports only.** Ports are `typing.Protocol`s in `application/ports/`. Gmail, the LLM SDKs and SQLAlchemy live in `infrastructure/`.
- **Only infrastructure may cross a context border.** `application/` and `domain/` of one context never import another context. To reach another context, define a local port and value object, and implement the adapter in your own `infrastructure/`.
- **Entrypoints are composition roots**, not contexts. They wire handlers from several contexts and own the process lifecycle. Per-context HTTP routes stay inside the context.
- **No code for future use.** A port, helper or table exists only when something calls it today.

## Bounded contexts today

| Context | Owns | State |
|---|---|---|
| `identity` | workspaces — the tenant registry, deliberately outside RLS so tenants can be listed | built (Step 1) |
| `mailbox` | the connected Gmail mailbox, its address and sync cursor | built (Step 2) |
| `messaging` | outbound and inbound messages, reply matching, intent classification, outbox events | built (Step 2) |
| `campaign` | campaigns, sequence steps, leads and their state machine | table stub; logic in Step 3 |

Tenancy: every tenant table has row-level security keyed by the session GUC `app.workspace_id`. The API sets it from the `X-Workspace-Id` header; the worker sets it from `MAILBOX_WORKSPACE_ID`. Tests run as the non-superuser role `outboxlab_app` so the policies are actually exercised.

## Target context map

The full model the sprint is walking toward. Names are the domain language; the code adds contexts only when the first consumer arrives.

**Identity & Access** — `Workspace` (aggregate root), `User`, `Membership`, `ApiKey`. Events: `WorkspaceCreated`, `MemberInvited`, `ApiKeyIssued`. Invariant: a user has exactly one role per workspace. Auth stays local-first (Postgres sessions, workspace API keys); external identity providers are future adapters, not part of the model.

**Mailbox Management** — `Mailbox` (root: address, provider, token reference, status, health), `Domain` (SPF / DKIM / DMARC state), `OAuthToken` inside the mailbox. Events: `MailboxConnected`, `TokenRefreshed`, `HealthDegraded`. Invariant: an `ACTIVE` mailbox has valid credentials.

**Campaign** — `Campaign` (root) with `Step` and `Lead`; lead states `PENDING` / `SCHEDULED` / `SENT` / `PAUSED` / `DONE` / `FAILED`. Events: `CampaignCreated`, `LeadAdded`, `StepScheduled`, `LeadPaused`, `LeadCompleted`, `LeadInvalidated`. Invariant: `Lead.state` changes only through the aggregate.

**Sending** — `SendTask` (root: mailbox, lead, step, schedule, attempts). Events: `MessageSent` (with the RFC 822 `Message-ID` for later matching), `MessageBounced`, `MessageDeferred`, `SendTaskFailed`. Invariant: no `MessageSent` without a valid rate-limit window. Today this lives inside `messaging`; it is the first extraction candidate (Step 5).

**Reply Handling** — `InboundMessage` (root), `Reply` linked to a lead. Value object `ReplyIntent`: `POSITIVE` / `NEGATIVE` / `OOO` / `UNSUBSCRIBE` / `UNCLEAR` (Step 3 adds `BOUNCE`). Events: `InboundReceived`, `ReplyMatched`, `ReplyClassified`. Invariant: a `Reply` exists only when the inbound message matched an outbound one. Today this also lives inside `messaging`.

**Billing** — parked. `Subscription`, `Invoice`, `MailboxQuota`.

## Hexagonal communication

Contexts never call each other directly. The contract between contexts is an event with a fixed JSON Schema in `contracts/events/<event>/v<n>.json`; the transport is just an adapter. Today the only transport is the Postgres outbox table written inside the same transaction as the state change ([ADR 0006](../adr/0006-transactional-outbox-inline.md)). A dispatcher and the first consumer arrive in Step 3. Moving to a broker later is an infrastructure migration with known risks (data ownership, backfill, retries, idempotency), not a rewrite.

A schema change means a new `v2.json` next to `v1.json` and a handler that accepts both versions.

**Flow 1 — a reply pauses a lead (Step 2 + Step 3):**

```
worker poll → Gmail adapter → InboundReceived
  → match by In-Reply-To / References → ReplyMatched
  → classify (rules or LLM) → ReplyClassified
  → campaign consumer: Campaign.pause_lead() → LeadPaused
  → sending consumer: cancel future send jobs
```

**Flow 2 — a bounce degrades a mailbox (Step 3+):**

```
Gmail adapter detects a delivery-status notification → intent BOUNCE
  → mark the address dead, write a suppression row
  → mailbox health recomputed; above threshold → HealthDegraded
```

## Key patterns

1. **Aggregate boundaries.** `Campaign` is the root for `Step` and `Lead`; lead state changes go through the aggregate.
2. **Domain events + transactional outbox.** Every state change writes its event in the same transaction. At-least-once delivery with idempotent handlers, no distributed transactions.
3. **CQRS lite.** Writes through aggregates and handlers; reads through plain queries (later: SQL views for metrics).
4. **Ports and adapters.** Domain and application know nothing about FastAPI, Gmail, the LLM vendors or Postgres. Use-case tests wire a real repository against a real database; route tests mock the handler.
5. **Provider neutrality at the seam.** Domain and ports use `provider_message_id`, `provider_thread_id`, `sync_cursor`; vendor names appear only inside `infrastructure/<vendor>/` ([ADR 0009](../adr/0009-provider-neutral-names.md)).

See also: [infrastructure](infrastructure.md), [ADR index](../adr/README.md).
