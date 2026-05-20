# Production image for apps/web — Next.js standalone build.
# Step 4 fills this out. For now, a Caddy-served placeholder.
FROM caddy:2.9-alpine AS runtime

WORKDIR /srv
COPY apps/web/index.html /srv/index.html

EXPOSE 3000
CMD ["caddy", "file-server", "--root", "/srv", "--listen", ":3000"]

# Step 4 layout (planned):
#   FROM node:22-alpine AS deps
#   RUN corepack enable
#   COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
#   RUN pnpm install --frozen-lockfile
#   FROM deps AS builder
#   COPY apps/web ./
#   RUN pnpm build
#   FROM node:22-alpine AS runtime
#   COPY --from=builder /app/.next/standalone ./
#   CMD ["node", "server.js"]
