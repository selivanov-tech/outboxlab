FROM node:26-alpine

ENV NEXT_TELEMETRY_DISABLED=1
# Node 25+ no longer ships corepack; the pnpm version matches packageManager in package.json.
ARG PNPM_VERSION=10.33.0
RUN npm install --global pnpm@${PNPM_VERSION}

# Dependencies and config are baked into the image at /app; compose bind-mounts only
# apps/web/src over /app/src. node_modules therefore never sits inside a bind mount
# (Docker hides a volume nested in one). Rebuild (`make rebuild`) after package.json,
# pnpm-lock.yaml or a config file changes.
WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./

EXPOSE 3000
CMD ["pnpm", "exec", "next", "dev", "--hostname", "0.0.0.0", "--port", "3000"]
