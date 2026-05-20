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

## Daily

```bash
make up          # start
make logs        # tail
make ps          # status
make shell-api   # bash into api
make shell-db    # psql into postgres
make down        # stop
make clean       # stop + drop volumes
```

`make help` lists everything.

## Package managers

- Python: `uv` (no pip, no poetry).
- Node: `pnpm` (no npm, no yarn, no bun lockfiles).
