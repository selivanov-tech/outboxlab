# ADR 0003 — Tenant isolation with row-level security

**Status:** accepted (Step 1); since Step 4 the API resolves the workspace from an API key and rejects the header in production ([ADR 0017](0017-workspace-api-keys.md))

## Context

Every tenant-owned table must be isolated per workspace. Doing it only in application code is easy to forget in one query; doing it in the database makes it a property of the schema.

## Decision

Tenant tables have `ENABLE` and `FORCE ROW LEVEL SECURITY` with a `workspace_isolation` policy on `workspace_id = current_setting('app.workspace_id')`. The API sets the GUC per request from the `X-Workspace-Id` header; the worker sets it from `MAILBOX_WORKSPACE_ID`. The tenant registry (`identity__workspaces`) is deliberately outside RLS so tenants can be listed.

The non-superuser role `outboxlab_app` is created outside migrations (`infra/postgres/bootstrap_app_role.sql`, mounted into the local postgres init directory and piped through `psql` in CI; run once by hand on Neon). Tests `SET LOCAL ROLE outboxlab_app` because `FORCE RLS` does not apply to a superuser.

## Consequences

- A missing GUC returns no rows rather than another tenant's rows.
- Migrations never touch roles, so production only needs a pre-made role with DML rights.
- The runtime role in production is still a decision to make before real multi-tenancy (see the parking lot).
