# ADR 0008 — The worker lives in the api project

**Status:** accepted (Step 2; replaces the separate `apps/worker-py`)

## Context

The Gmail poller needs the messaging handlers, the mailbox gateway, the repositories and the database engine — the same code as the API. A separate Python project meant a second lockfile, a second image and duplicated wiring.

## Decision

The worker is `app/entrypoints/worker.py` inside `apps/api`, run as `python -m app.entrypoints.worker`. It is a composition root that imports `app.*` directly. It deploys as its own fly app (`outboxlab-worker`) from the same image, with the CMD overridden by a process group, and with its own secrets. CI deploys only the API; the worker is deployed by hand with `make deploy-worker`.

## Consequences

- One project, one lockfile, one image; pyright and ruff cover the worker for free.
- The Go sender (Step 5) is a genuinely separate service by design, not by accident of packaging.
- Deploying the API does not restart the worker; schema changes must stay compatible with the running worker or the worker must be redeployed right after.
