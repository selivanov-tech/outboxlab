# Step 1 — Walking skeleton deployed

[← Back to the plan](README.md)

**Status: done.** [PR #1](https://github.com/selivanov-tech/outboxlab/pull/1) "Step 1: walking skeleton — identity BC, workspaces, CI".

## Goal

No emails yet. Get a live, deployed backbone: FastAPI + Neon + the DDD layout + baseline tables + health / version endpoints on fly.io. The debug endpoint is available only outside production.

## What was built

**Application**

- FastAPI + Pydantic v2 + SQLAlchemy 2.0 async (`apps/api/pyproject.toml`).
- Alembic with a hand-written first migration (`alembic/versions/0001_baseline.py`), not autogenerate, so the DDL and RLS policies stay reviewable.
- DDD layers for the `identity` context only, plus a `campaign` table placeholder. Other contexts (`mailbox`, `sending`, `reply`) were removed under the "no code for future use" rule and return when the first real consumer appears — see [ADR 0012](../adr/0012-no-code-for-future-use.md).
- Baseline tables: `workspaces` and `campaigns` — only the ones with a consumer in Step 1. UUID primary keys are generated application-side.
- Idempotent seed of a single default workspace with a deterministic UUID, run only via `make seed` (no auto-seed on startup).
- Workspace-aware repository layer: a `current_workspace_id` context variable set by middleware from the `X-Workspace-Id` header. A malformed header is a `400`, not a silent drop. This is a placeholder until real auth.
- CQRS path for `GET /workspaces/me`: route → `GetMyWorkspaceHandler` → `WorkspaceRepositoryPort` → `WorkspaceRepository` → DB → JSON.
- Shared UTC clock (`app/shared/util/clock.now()`) as the single time source.
- RLS smoke test: RLS enabled and forced on `campaigns` (the only tenant table in the baseline). The test switches to the non-superuser role `outboxlab_app` so `FORCE ROW LEVEL SECURITY` actually applies. See [ADR 0003](../adr/0003-row-level-security-per-workspace.md).
- Endpoints: `GET /health`, `GET /version`, `GET /debug/state` (non-production only), `GET /workspaces/me`.

**Deploy and CI**

- Deployed to fly.io, connected to Neon through the `DATABASE_URL` secret; `API_DOMAIN` added as a second required secret.
- Migrations run automatically in the fly `release_command` (`alembic upgrade head`) before serving machines start — see [ADR 0010](../adr/0010-fly-deploy-with-release-migrations.md).
- The app role `outboxlab_app` is created outside migrations (`infra/postgres/bootstrap_app_role.sql`), mounted into the local postgres init directory and piped through `psql` in CI.
- `make deploy` moved into `infra/make/deploy.mk`, which the dev Makefile includes and CI calls standalone.
- CI (`.github/workflows/ci.yml`): `api-tests` (postgres 17 service, role bootstrap, migrations, seed, pytest), `typecheck` (pyright), `lint` (ruff format + check), `leak-check`, and `deploy-api` gated by all four and by `environment: production`, only on push to `main`.
- Test pyramid: handler tests run against a real database; route tests live in `tests/unit/` and mock the handler through FastAPI `dependency_overrides`.
- asyncpg / Neon SSL fix: a helper strips libpq-only query parameters (`sslmode`, `channel_binding`) and maps `sslmode` to asyncpg's `ssl=`. It is used in both places that open a connection: the app engine and `alembic/env.py`.

## Success signal

✅ Public fly URL answers `200`, Neon migrations green, the seeded workspace is visible via the API. Locally: `make migrate` + `make seed` + `make test` green (28 tests at the time), `make typecheck` 0 errors, `make lint` clean.
