# ADR 0017 — Minimal workspace API keys

**Status:** accepted (Step 4). A step toward the parked "full auth", not a replacement for it. Refines [ADR 0003](0003-row-level-security-per-workspace.md): the API resolves the workspace from a key instead of trusting a header.

## Context

Until Step 3 the API took the workspace from the `X-Workspace-Id` header, so every write route was mounted outside production only. The demo needs the campaign routes and the viewer on the deployed URL, and Step 6 needs a credential that an MCP client can send on every call. Users, sessions and OAuth are still parked.

## Decision

- **Table** `identity__api_keys` (migration `0006`): `id`, `workspace_id`, `prefix` (unique), `secret_hash`, `created_at`, `revoked_at`. Like `identity__workspaces`, it is outside RLS, because it is read before the workspace is known.
- **Key format** `olab_<prefix>_<secret>`: `prefix` is 12 hex characters used for lookup; `secret` is 32 random bytes, URL-safe. Only the SHA-256 of the secret is stored. The comparison is constant-time. SHA-256 without a salt is enough for a high-entropy random secret; it would not be enough for a password.
- **Issuing:** `python -m app.entrypoints.issue_api_key` (`make api-key` locally) prints a new key for `MAILBOX_WORKSPACE_ID` once. There are no key-management routes and no rotation. A key is revoked by setting `revoked_at`.
- **Middleware:** `Authorization: Bearer <key>` resolves the workspace for the request; an unknown, wrong or revoked key is `401` on every route. `X-Workspace-Id` is **rejected in production** (`401`) and still accepted locally and in tests. With no credentials, routes that need a workspace answer `401`.
- **Mounting** (`create_app(settings)`): health, version, `/workspaces/me`, the campaign routes, `/debug/state` (now scoped to the caller's workspace) and `/viewer/` are served in every environment. `/send-test-email` stays non-production.

## Consequences

- The deployed API can run the demo with one key. Real sends from production still need the worker app deployed with its Google secrets.
- Each authenticated request makes one indexed lookup in `identity__api_keys`.
- Still missing for real multi-tenancy: users, memberships, key management and rotation, per-key scopes, rate limits per key, and the runtime database role decision.
