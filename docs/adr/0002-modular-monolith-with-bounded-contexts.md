# ADR 0002 — Modular monolith with bounded contexts

**Status:** accepted (Step 1, layout refined in Step 2)

## Context

The domain has clear sub-domains (identity, mailbox, campaign, sending, reply handling, billing). Microservices would multiply deploys and contracts before there is any load. A flat monolith would let modules call each other freely and make later extraction expensive.

## Decision

One FastAPI codebase organised as bounded contexts under `app/contexts/<bc>/`, each with `domain / application / infrastructure / presentation` layers. Cross-cutting code lives in `app/shared/`; process roots (`api.py`, `worker.py`, `seed.py`) live flat in `app/entrypoints/` because they compose handlers from several contexts and own the process lifecycle.

Rules:

- Domain and application depend on ports (`typing.Protocol`) only.
- **Only infrastructure may cross a context border.** `application/` and `domain/` of one context never import another context. To use another context, define a local port and value object; implement the adapter in your own `infrastructure/`.
- Per-context HTTP routes stay inside the context's `presentation/`; entrypoints only wire.
- The folder is named `contexts/`, not `src/` (a meaningless import segment) or `core/` (which would swallow `shared/`, which is cross-cutting, not a context).

## Consequences

- The module structure is visible from the top level: `contexts/`, `shared/`, `entrypoints/`.
- Extracting a context later (Sending first) is a known cost: it already talks through ports and events.
- Some duplication of small value objects across contexts is accepted over shared domain code.
