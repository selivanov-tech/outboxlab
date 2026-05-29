# CI-facing make targets. Self-contained: no COMPOSE / .env-domain dependency,
# so CI can invoke it standalone via `make -f infra/make/deploy.mk <target>`.
# The dev Makefile includes this file so `make deploy` / `make check-leaks`
# keep working locally too.

# ---- Deploy ----

# FLY: binary name (local installs `fly`; the CI setup-flyctl action installs `flyctl`).
# FLY_DEPLOY_FLAGS: extra flags (CI passes --remote-only to use fly's builder, no local docker).
FLY ?= fly
FLY_DEPLOY_FLAGS ?=

.PHONY: deploy
deploy:  ## Deploy api to fly.io (GIT_SHA = current HEAD)
	@command -v $(FLY) >/dev/null 2>&1 || { echo "$(FLY) not found. Install: brew install flyctl"; exit 1; }
	$(FLY) deploy \
		-c infra/prod/fly/api.fly.toml \
		--dockerfile infra/prod/api/Dockerfile \
		--build-arg GIT_SHA=$$(git rev-parse --short HEAD) \
		$(FLY_DEPLOY_FLAGS)

# ---- Guards ----

.PHONY: check-leaks
check-leaks:  ## Fail if any tracked file leaks local/prod hostnames
	@if git ls-files -z 2>/dev/null | xargs -0 grep -lEI '\.local\.|\.fly\.dev|ssel\.asia' 2>/dev/null | grep -v '^\.env\.example$$' | grep .; then \
		echo ""; echo "Hostname leak detected in tracked files. Move domains to .env."; exit 1; \
	else \
		echo "No hostname leaks in tracked files."; \
	fi
