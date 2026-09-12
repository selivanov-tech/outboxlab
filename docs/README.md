# OutboxLab docs

Public, technical documentation for the OutboxLab sprint. Everything here describes the code in this repository or the plan for it. Personal notes, credentials and hostnames are deliberately kept out.

| Folder | What is in it |
|---|---|
| [`plan/`](plan/README.md) | The 7-step build plan: one page per step with goal, checklist, decisions and status. Each "Step N" pull request links to its page. |
| [`architecture/`](architecture/overview.md) | Bounded contexts, hexagonal communication, event contracts, and the infrastructure choices (Neon, Postgres-only queues, fly.io). |
| [`adr/`](adr/README.md) | Architecture decision records: the decisions that shape the code and why they were taken. |

Start with [the plan](plan/README.md) if you want to know what a "Step N" PR means, and with the [ADR index](adr/README.md) if you want to know why the code looks the way it does.
