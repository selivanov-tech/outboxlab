.DEFAULT_GOAL := help
SHELL := /bin/bash

COMPOSE := docker compose -f infra/dev/docker-compose.yml --env-file .env
CERT_DIR := infra/dev/proxy/certs

# Domains are read from .env (gitignored). Never hardcode them here.
# tr -d '\r' strips CRLF if .env was edited on Windows; $(strip) trims whitespace.
API_DOMAIN := $(strip $(shell test -f .env && grep -E '^API_DOMAIN=' .env | head -1 | cut -d= -f2- | tr -d '\r'))
WEB_DOMAIN := $(strip $(shell test -f .env && grep -E '^WEB_DOMAIN=' .env | head -1 | cut -d= -f2- | tr -d '\r'))
LOCAL_DOMAINS := $(strip $(API_DOMAIN) $(WEB_DOMAIN))

define require_domains
@test -n "$(API_DOMAIN)" || { echo "API_DOMAIN not set in .env (run: make env, then edit .env)"; exit 1; }
@test -n "$(WEB_DOMAIN)" || { echo "WEB_DOMAIN not set in .env (run: make env, then edit .env)"; exit 1; }
endef

# CI-facing targets (deploy, check-leaks) live in their own fragment so CI can
# invoke them standalone with `make -f infra/make/deploy.mk <target>`.
include infra/make/deploy.mk

.PHONY: help
help:  ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---- First-run setup ----

.PHONY: setup
setup: env  ## First-time bootstrap: create .env, then print next steps
	@echo ""
	@echo "Next steps (run in order, after editing .env):"
	@echo "  1. Edit .env       — set API_DOMAIN, WEB_DOMAIN, GOOGLE_* secrets"
	@echo "  2. make certs      — generate local TLS certs (reads domains from .env)"
	@echo "  3. make hosts-add  — point local domains at 127.0.0.1 (uses sudo)"
	@echo "  4. make up         — start containers"

.PHONY: env
env:  ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; else echo ".env already exists, skipping"; fi

.PHONY: certs
certs:  ## Generate local TLS certs via mkcert
	$(require_domains)
	@command -v mkcert >/dev/null 2>&1 || { echo "mkcert not found. Install: brew install mkcert nss"; exit 1; }
	@mkcert -install
	@mkdir -p $(CERT_DIR)
	@cd $(CERT_DIR) && mkcert -cert-file local.pem -key-file local-key.pem $(LOCAL_DOMAINS)
	@echo "Certs written to $(CERT_DIR)/"

.PHONY: hosts-check
hosts-check:  ## Print /etc/hosts entries needed for local domains
	$(require_domains)
	@echo "Add to /etc/hosts (or run: make hosts-add):"
	@for d in $(LOCAL_DOMAINS); do echo "  127.0.0.1 $$d"; done

.PHONY: hosts-add
hosts-add:  ## Append missing entries to /etc/hosts (uses sudo)
	$(require_domains)
	@for d in $(LOCAL_DOMAINS); do \
		if grep -Eq "(^|[[:space:]])$$d([[:space:]]|$$)" /etc/hosts; then \
			echo "$$d already in /etc/hosts"; \
		else \
			echo "127.0.0.1 $$d" | sudo tee -a /etc/hosts >/dev/null && echo "Added $$d"; \
		fi \
	done

# ---- Compose lifecycle ----

.PHONY: up
up:  ## Start all containers
	$(require_domains)
	$(COMPOSE) up -d
	@echo ""
	@echo "API:    https://$(API_DOMAIN)"
	@echo "Web:    https://$(WEB_DOMAIN)"
	@echo "Logs:   make logs"

.PHONY: down
down:  ## Stop all containers
	$(COMPOSE) down

.PHONY: restart
restart: down up  ## Restart all containers

.PHONY: build
build:  ## Build images
	$(COMPOSE) build

.PHONY: rebuild
rebuild: down build up  ## Stop, rebuild images, start

# ---- Observability ----

.PHONY: logs
logs:  ## Tail logs for all services
	$(COMPOSE) logs -f --tail=100

.PHONY: ps
ps:  ## Show running services
	$(COMPOSE) ps

# ---- Shells ----

.PHONY: shell-api
shell-api:  ## Open shell in api container
	$(COMPOSE) exec api /bin/bash

.PHONY: shell-worker
shell-worker:  ## Open shell in worker container
	$(COMPOSE) exec worker /bin/bash

.PHONY: shell-db
shell-db:  ## Open psql in postgres container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-outboxlab} -d $${POSTGRES_DB:-outboxlab}

# ---- Database ----

.PHONY: migrate
migrate:  ## Apply pending migrations against local postgres
	$(COMPOSE) exec api uv run alembic upgrade head

.PHONY: migration
migration:  ## Create a new migration (use: make migration name="add foo")
	@test -n "$(name)" || { echo "Usage: make migration name=\"description\""; exit 1; }
	$(COMPOSE) exec api uv run alembic revision --autogenerate -m "$(name)"

.PHONY: seed
seed:  ## Seed default workspace into local DB
	$(COMPOSE) exec api uv run python -m app.identity.infrastructure.seed

.PHONY: test
test:  ## Run api tests
	$(COMPOSE) exec api uv run pytest -q

.PHONY: typecheck
typecheck:  ## Run pyright on api + worker (inside containers)
	@echo "==> typecheck api"
	$(COMPOSE) exec api uv run pyright
	@echo "==> typecheck worker"
	$(COMPOSE) exec worker uv run pyright

.PHONY: lint
lint:  ## Check formatting + lint with ruff, read-only (matches CI)
	@echo "==> lint api"
	$(COMPOSE) exec api uv run ruff format --check app tests
	$(COMPOSE) exec api uv run ruff check app tests
	@echo "==> lint worker"
	$(COMPOSE) exec worker uv run ruff format --check main.py
	$(COMPOSE) exec worker uv run ruff check main.py

.PHONY: format
format:  ## Auto-format + autofix with ruff (writes changes)
	@echo "==> format api"
	$(COMPOSE) exec api uv run ruff format app tests
	$(COMPOSE) exec api uv run ruff check --fix app tests
	@echo "==> format worker"
	$(COMPOSE) exec worker uv run ruff format main.py
	$(COMPOSE) exec worker uv run ruff check --fix main.py

# ---- Cleanup ----

.PHONY: clean
clean:  ## Remove containers, networks, volumes
	$(COMPOSE) down -v --remove-orphans

.PHONY: nuke
nuke:  ## clean + remove built images
	$(COMPOSE) down -v --rmi local --remove-orphans
