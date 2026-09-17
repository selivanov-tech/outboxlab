# ADR 0021 — The web console is a Next.js app that fronts the API (backend-for-frontend)

**Status:** accepted (Step 8). Supersedes [ADR 0016](0016-viewer-served-by-the-api.md) as the operator UI; the static viewer stays until the console is deployed, then it is removed.

## Context

The static viewer of ADR 0016 is read-only. Creating a campaign, adding leads and starting it were API or MCP calls. An operator needs one place to do all three and to watch leads move. The API authenticates with a workspace API key, which must not live in browser JavaScript, and the API has no CORS setup.

## Decision

- `apps/web` is a Next.js (App Router) app in TypeScript. It follows Feature-Sliced Design: `shared → entities → features → app`; lower layers never import higher ones. Server Components by default; `'use client'` only for forms, the live refresh timer and the active navigation link.
- **Backend-for-frontend.** The browser never calls the API. Pages read through Server Components and write through Server Actions; both run on the Next.js server and call the API with the workspace credential. No CORS, no second public API surface.
- **Session.** The connect form takes an API key (or a workspace id, which only a non-production API accepts), checks it with `GET /workspaces/me`, and stores it in an `HttpOnly`, `SameSite=Strict`, `Secure` (in production) cookie. The cookie value is the credential itself: there is no server-side session store and no second secret to manage. A `401` from the API at any point clears the cookie and returns to the connect page.
- **Typed client from the contract.** `contracts/openapi/api-v1.json` is exported from the production FastAPI app (`make openapi`). An API test fails when the committed file is stale, and the web CI job fails when the generated TypeScript types do not match it. `/debug/state` got a response model so the console reads it with types.
- **Live view without a client data layer.** A small client component calls `router.refresh()` on a timer while the tab is visible; Server Components re-render with fresh data. No client-side fetch, cache or state library.
- **Deploy.** `outboxlab-web` is a separate fly app built from `infra/prod/web/Dockerfile` (Next.js standalone output). It is deployed by hand with `make deploy-web`, like the worker; CI builds and tests it but deploys only the API. Its one setting is `OUTBOXLAB_API_URL`, kept as a fly secret so no hostname lands in tracked files.
- pnpm is the package manager for `apps/web`; the image installs a pinned pnpm with npm because Node 25+ no longer ships corepack.

## Consequences

- The API key is never readable by page scripts, and the API keeps a single auth mechanism.
- Every page view costs a server-to-server API call; fine at this scale, and cacheable per route later.
- A stolen cookie is a stolen API key until the key is revoked; the mitigation is the cookie flags plus key revocation (`revoked_at`), not a session layer.
- `WEB_DOMAIN` and the `web` compose service are back, now with a real consumer.
- Two UIs exist until the console is deployed; removing `/viewer` is the follow-up.
