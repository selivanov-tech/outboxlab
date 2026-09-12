# ADR 0010 — fly.io deploy gated by CI, migrations in the release command

**Status:** accepted (Step 1)

## Context

A public URL was needed from Step 1. Deploys must not skip tests, and a broken migration must never reach live traffic.

## Decision

- Every PR runs four CI jobs: tests against a Postgres 17 service (role bootstrap, migrations, seed, pytest), pyright, ruff, and a hostname leak check.
- On push to `main`, a `deploy-api` job runs only after all four pass (`needs:`) and inside the `production` GitHub environment. It calls `make -f infra/make/deploy.mk deploy` with the remote builder.
- The api `fly.toml` has `release_command = "alembic upgrade head"`, which runs in a one-off VM before serving machines start. A non-zero exit fails the deploy.
- `Settings` reads required env at import time in both the app and `alembic/env.py`; local, CI and the release command all set `DATABASE_URL`, `API_DOMAIN`, `APP_ENV`.

## Consequences

- `main` is always deployed; a docs-only merge also triggers a (harmless) deploy.
- The worker is not deployed by CI (ADR 0008).
- The asyncpg URL helper must be used in both the app engine and Alembic, or only one of the two paths works against Neon.
