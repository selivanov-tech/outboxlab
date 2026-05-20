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

# ---- Cleanup ----

.PHONY: clean
clean:  ## Remove containers, networks, volumes
	$(COMPOSE) down -v --remove-orphans

.PHONY: nuke
nuke:  ## clean + remove built images
	$(COMPOSE) down -v --rmi local --remove-orphans

# ---- Guards ----

.PHONY: check-leaks
check-leaks:  ## Fail if any tracked file leaks local/prod hostnames
	@if git ls-files -z 2>/dev/null | xargs -0 grep -lEI '\.local\.|\.fly\.dev|ssel\.asia' 2>/dev/null | grep -v '^\.env\.example$$' | grep .; then \
		echo ""; echo "Hostname leak detected in tracked files. Move domains to .env."; exit 1; \
	else \
		echo "No hostname leaks in tracked files."; \
	fi
