# Step 0 — Local dev stack and deploy path

[← Back to the plan](README.md)

**Status: done.** Commit `a1470e1` "Step 0: scaffold local dev stack and fly deploy path".

## Goal

Remove external blockers before writing any domain code: Gmail OAuth, the fly.io deploy path, Neon, the GitHub repo, secrets handling, and a fallback plan for each of them.

## What was set up

**Accounts and tooling**

- CLIs logged in: `fly`, `gcloud`, `gh`. Docker on the host; runtime tools (`uv`, `psql`) live inside the dev containers so the host is not a hidden part of the build.
- `uv` pinned in the images. Go is not installed until Step 5.
- Env strategy: `.env` plus Docker Compose `env_file`. `.env.example` is committed with placeholders; `.env` is git-ignored and holds real domains and secrets.
- Node package manager: `pnpm` only. No `package-lock.json` or `bun.lockb`.

**Google / Gmail OAuth**

- OAuth consent screen in External / Testing mode with a single test user.
- Minimal scopes: `gmail.send` and `gmail.readonly`.
- OAuth client of type "Web application". The redirect URI is derived at runtime as `https://<API_DOMAIN>/auth/google/callback`, so it cannot drift from the configured domain; register that exact URL per environment.
- Local HTTPS: Caddy reverse proxy in `infra/dev/`, certificates via `mkcert` (`make certs`), `/etc/hosts` entries via `make hosts-add`. Domains live only in `.env`; `make check-leaks` fails if a tracked file contains one.

**fly.io**

- App `outboxlab-api`, region `iad`, hello-world deploy with a live `/health`.
- Secrets flow (`fly secrets set / list / unset`) and logs flow verified.
- `fly.toml` skeletons for api, worker and web in `infra/prod/fly/`: internal port, `force_https`, `auto_stop_machines`, `min_machines_running = 0`.

**Database**

- Neon project created. Decision: local development always uses the compose `postgres` service; Neon is used only from fly through secrets.
- `psql` connectivity verified from the dev container (`make shell-db`).

**Repository**

- Monorepo: `apps/{api,web}`, `contracts/`, `docs/`, `infra/dev/` (compose, dev Dockerfiles, Caddy), `infra/prod/` (prod Dockerfiles, `fly/`).
- Compose services: `api`, `worker`, `web`, `postgres`, `proxy`. `make up` starts all five with health checks.
- Minimal README: goal, stack, layout, first-time setup, daily commands, package managers.

## Fallback plan agreed up front

- OAuth consent UI → manual refresh-token flow.
- LLM classifier → deterministic classifier.
- UI builder → API / script.

## Success signal

✅ `make up` starts all containers with health checks, the prod image builds and deploys to fly without errors, `/health` answers on the public URL, the repo is on GitHub, `psql` connectivity confirmed. Step 1 does not wait on any external console.

Some follow-ups moved to later steps: the manual token flow to [Step 2](step-2-real-email-loop.md), a smoke script to [Step 4](step-4-hardening-and-demo.md).
