# OutboxLab

Mini cold-email outreach infrastructure. Built as a 7-step proof-of-work sprint to demonstrate DDD, hexagonal architecture, and a Postgres-only operational stack (no Redis, no extra brokers).

## Stack

- API: FastAPI (Python 3.14, uv, SQLAlchemy 2.0 async, Pydantic v2)
- Worker: Python (sender + IMAP poller). Go extraction in phase 2.
- Web: Next.js minimal state viewer.
- DB: local postgres (dev) / Neon (prod).
- Queue / cache / rate-limit: postgres-only (`SELECT FOR UPDATE SKIP LOCKED` + advisory locks).
- Deploy: fly.io.

## Layout

```
apps/
  api/         FastAPI
  worker-py/   sender + IMAP poller
  web/         state viewer
contracts/     event JSON Schemas (versioned)
infra/
  dev/         docker-compose + dev Dockerfiles + Caddy proxy
  prod/        prod Dockerfiles + fly.toml
  make/        shared make fragments (deploy.mk)
docs/          ADRs
```

## First-time setup

Prereqs: a Docker engine, `mkcert` (`brew install mkcert nss`), `make`.

> macOS / Apple Silicon: Docker Desktop, OrbStack, or Colima all work. OrbStack is
> the fastest path if you hit networking quirks on ports 80/443 with Docker Desktop.

```bash
make env         # copy .env.example -> .env
# edit .env: set API_DOMAIN, WEB_DOMAIN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
make certs       # generate TLS certs for your domains
make hosts-add   # append /etc/hosts entries (sudo)
make up          # start containers
```

`make setup` runs `make env` and prints the next steps — you still need to edit `.env`
before `make certs` so mkcert sees your domains.

Open URLs are printed by `make up` and live only in your `.env`.

After `make up`:

```bash
make migrate     # apply Alembic migrations to local postgres
make seed        # insert the default workspace (idempotent)
make test        # run unit + integration tests
make lint        # ruff format-check + lint (same as CI)
```

Endpoints (replace with your `API_DOMAIN`):

- `GET /health` — liveness
- `GET /version` — version + git SHA + APP_ENV
- `GET /debug/state` — DB ping + workspace count

## Daily

```bash
make up          # start
make logs        # tail
make ps          # status
make shell-api   # bash into api
make shell-db    # psql into postgres
make migrate     # apply pending Alembic migrations
make test        # run pytest
make typecheck   # pyright (api + worker)
make lint        # check format + lint with ruff
make format      # auto-format + autofix with ruff (writes changes)
make down        # stop
make clean       # stop + drop volumes
```

`make help` lists everything.

## Adding a migration

```bash
# edit ORM models in apps/api/app/<bc>/infrastructure/db/models.py
make migration name="describe the change"
# review apps/api/alembic/versions/<new_file>.py
make migrate
```

Baseline migration is hand-written (`alembic/versions/0001_baseline.py`) so its
DDL + RLS policies stay reviewable; subsequent migrations use autogenerate.

## RLS app role

The migration assumes a non-superuser role `outboxlab_app` exists at the cluster
level. Tests `SET LOCAL ROLE outboxlab_app` to exercise RLS policies as a
non-superuser (FORCE RLS doesn't help under a superuser).

- **Local (compose)**: created automatically by
  `infra/postgres/bootstrap_app_role.sql`, mounted into the postgres image's
  `/docker-entrypoint-initdb.d/`. Runs once on an empty data dir, so re-runs
  need `make clean` first.
- **CI**: a workflow step pipes the same SQL through `psql` before migrations.
- **Prod (Neon)**: run the same SQL once against your Neon DB via the Neon SQL
  editor (or `psql` with the direct URL). Migrations themselves never touch
  roles, so the runtime app role only needs SELECT/INSERT/UPDATE/DELETE on the
  schema — no CREATEROLE required.

## CI

GitHub Actions runs on every PR:

- **api-tests** — Postgres 17 service, app-role bootstrap, migrations, seed, pytest.
- **typecheck** — pyright on api + worker.
- **lint** — ruff `format --check` + `check` on api + worker (pinned 0.15.15).
- **leak-check** — fails if a tracked file leaks a hostname.

On merge to `main`, the **deploy-api** job ships the api to fly.io. It runs only
after all four checks pass (`needs:`) and inside the `production` environment.

One-time setup: add a fly deploy token as the `FLY_API_TOKEN` secret (repo or
the `production` environment):

```bash
fly tokens create deploy -a outboxlab-api
```

The CI-facing targets (`deploy`, `check-leaks`) live in `infra/make/deploy.mk`
so CI calls them standalone; the dev Makefile includes the same file, so
`make deploy` / `make check-leaks` still work locally.

## Deploy (fly.io)

Merging to `main` auto-deploys through the CI **deploy-api** job. To deploy by
hand:

```bash
# one-time: bootstrap the app role on Neon (Neon SQL editor or psql).
psql "$NEON_DIRECT_URL" -f infra/postgres/bootstrap_app_role.sql

# one-time: point fly at Neon (direct, non-pooler URL for migrations) and set
# the API domain — Settings requires it, and the release migration builds it.
fly secrets set -a outboxlab-api \
  DATABASE_URL="postgresql+asyncpg://<neon-url>" \
  API_DOMAIN="<your-api-domain>"

# every deploy (wraps fly deploy; see infra/make/deploy.mk)
make deploy
```

The `[deploy] release_command` in `api.fly.toml` runs `alembic upgrade head`
in a one-off VM before serving machines start, so a broken migration fails
the deploy rather than reaching live traffic.

## Package managers

- Python: `uv` (no pip, no poetry).
- Node: `pnpm` (no npm, no yarn, no bun lockfiles).
