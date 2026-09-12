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
