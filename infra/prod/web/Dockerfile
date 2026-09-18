# Production image for apps/web — Next.js standalone output, no package manager at runtime.
# Build context is the repo root (passed as `.` by fly deploy / docker build).
FROM node:26-alpine AS builder

ENV NEXT_TELEMETRY_DISABLED=1
# Node 25+ no longer ships corepack; the pnpm version matches packageManager in package.json.
ARG PNPM_VERSION=10.33.0
RUN npm install --global pnpm@${PNPM_VERSION}

WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM node:26-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
CMD ["node", "server.js"]
