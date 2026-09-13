# ADR 0016 — The state viewer is a static page served by the API

**Status:** accepted (Step 4)

## Context

The demo needs a read-only view of campaigns, leads, lead states and reply intents that refreshes while a reply arrives. The repository carried an `apps/web` placeholder: a static page served by Caddy, a `web` compose service, a prod Dockerfile and a fly config for `outboxlab-web`. It was waiting for a Next.js app. A separate web app means a second deploy, a second domain (`WEB_DOMAIN`) and CORS between two origins, and the viewer only reads JSON the API already serves.

## Decision

- The viewer is one HTML file and one vanilla JavaScript file under `apps/api/app/shared/presentation/viewer/static/`, mounted by the API at `/viewer/` with Starlette `StaticFiles`. There is no build step and no Node toolchain.
- It calls the API on the same origin: `GET /campaigns`, `GET /campaigns/{id}`, `GET /debug/state`. It refreshes every 5 seconds. It sends an API key (`Authorization: Bearer`) or, outside production, a workspace id. The credentials live in `sessionStorage` only.
- Values are rendered with `textContent`, never as HTML.
- The placeholder is removed in the same change: `apps/web`, the `web` compose service and its Dockerfiles, `infra/prod/fly/web.fly.toml`, the Caddy site and `WEB_DOMAIN`. `API_DOMAIN` is now the only domain (refines [ADR 0011](0011-domains-only-in-env.md)).
- Creating campaigns stays an API call.

## Consequences

- The viewer is deployed with the API and works wherever the API works: locally at `https://<api-domain>/viewer/` and on fly.
- No CORS configuration and no second fly app. An already created `outboxlab-web` fly app, if one exists, is no longer deployed from this repository and can be destroyed by hand.
- A create or edit UI would bring a real frontend project back; that is parked until it is needed.
