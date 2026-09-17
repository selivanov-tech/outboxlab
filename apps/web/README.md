# apps/web — operator console

Next.js (App Router) console for OutboxLab. Decision record: [ADR 0021](../../docs/adr/0021-nextjs-web-console.md).

## Rules

- **The browser never calls the API.** Reads happen in Server Components, writes in Server Actions; both go through `src/shared/api` and `src/entities/*/api`. No `fetch` in components.
- **Feature-Sliced Design:** `shared → entities → features → app`. A lower layer never imports a higher one.
- A slice's `index.ts` is safe to import anywhere, client components included. Code that runs only on the server (it imports `server-only`) is exported from the slice's `server.ts`.
- Server Components by default; `'use client'` only when the browser is needed (forms with pending state, timers, the active nav link).
- Types come from `contracts/openapi/api-v1.json`. After an API change run `make openapi` from the repo root. Never edit `src/shared/api/generated`.
- Logic lives in `lib/` or `model/` as pure functions with a `*.test.ts` next to it; components stay thin.
- Times are shown in UTC (`src/shared/lib/format.ts`), the clock the daily send cap uses.

## Commands

```bash
pnpm install
OUTBOXLAB_API_URL=http://localhost:8000 pnpm dev   # or use the `web` compose service behind WEB_DOMAIN
pnpm api:generate                                   # regenerate types from the contract
```

Gate (same as CI, or `make web-ready` from the repo root):

```bash
pnpm api:check && pnpm lint && pnpm format:check && pnpm type-check && pnpm test && pnpm build
```
