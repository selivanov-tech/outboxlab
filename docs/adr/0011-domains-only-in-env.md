# ADR 0011 — Hostnames live only in `.env`

**Status:** accepted (Step 0)

## Context

Local HTTPS with real-looking domains is needed for Google OAuth redirect URIs, and the deployed app has public hostnames. Committing them to a public repository ties the code to one person's setup and leaks infrastructure details.

## Decision

All domains come from `API_DOMAIN` / `WEB_DOMAIN` in the git-ignored `.env`. Caddy reads them as environment placeholders, the Makefile reads them for certificates and hosts entries, and the OAuth redirect URI is derived at runtime from `API_DOMAIN`. `.env.example` holds placeholders only. `make check-leaks` (also a CI job) fails if any tracked file contains a local or production hostname pattern.

## Consequences

- Anyone can clone the repo and use their own domain without editing tracked files.
- The redirect URI cannot drift from the configured domain.
- Documentation must use placeholders such as `<api-domain>`.
