# Architecture decision records

Short records of the decisions that shape this codebase. Format: context → decision → consequences. Status is `accepted` unless stated otherwise. Newer records may refine older ones; they say so explicitly.

| # | Decision |
|---|---|
| [0001](0001-postgres-only-operational-stack.md) | Postgres-only operational stack: no Redis, no brokers |
| [0002](0002-modular-monolith-with-bounded-contexts.md) | Modular monolith with bounded contexts; only infrastructure crosses a border |
| [0003](0003-row-level-security-per-workspace.md) | Tenant isolation with row-level security keyed by a session GUC |
| [0004](0004-gmail-api-for-send-and-receive.md) | Gmail API for both send and receive; manual refresh-token auth |
| [0005](0005-llm-classifier-behind-a-port.md) | Intent classifier: LLM behind a port, provider selectable, deterministic fallback, on by default |
| [0006](0006-transactional-outbox-inline.md) | Transactional outbox written inline, no dispatcher until the first consumer |
| [0007](0007-bc-prefixed-table-names.md) | Every table is prefixed with its bounded context |
| [0008](0008-worker-in-the-api-project.md) | The worker lives in the api project and deploys as a separate fly app from the same image |
| [0009](0009-provider-neutral-names.md) | Provider-neutral names in domain and ports; no provider discriminator until a second provider exists |
| [0010](0010-fly-deploy-with-release-migrations.md) | fly.io deploy gated by CI, migrations in the release command |
| [0011](0011-domains-only-in-env.md) | Hostnames live only in `.env`; a leak check guards tracked files |
| [0012](0012-no-code-for-future-use.md) | No code for future use |
| [0013](0013-outbox-consumer-processed-events.md) | Outbox consumer: dispatcher in the worker with a processed-events set; event versions in the payload |
| [0014](0014-send-job-queue-contract.md) | Send-job queue contract: claim with `SKIP LOCKED` and a lease, at-least-once sending, frozen job payload |
| [0015](0015-sending-guards-in-messaging.md) | Sending guards in the messaging send path: suppression, advisory lock per mailbox, daily cap per UTC day |
| [0016](0016-viewer-served-by-the-api.md) | The read-only state viewer is a static page served by the API; the web placeholder and `WEB_DOMAIN` are removed |
| [0017](0017-workspace-api-keys.md) | Minimal workspace API keys: Bearer key resolves the workspace; the workspace header is rejected in production |
| [0018](0018-go-sender-claims-and-hands-off.md) | Go sender claims send jobs with the shared statement and hands each job to an internal API route |
