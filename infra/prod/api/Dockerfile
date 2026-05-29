# Production image for apps/api — multi-stage, slim runtime, no source mount.
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.11.17
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Build context is repo root (passed as `.` by fly deploy / docker build).
# --frozen: prod must match the committed lock exactly. Bump via `uv lock` in dev.
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev

# Runtime
FROM python:3.14-slim AS runtime

ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    GIT_SHA=${GIT_SHA}

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app apps/api/app /app/app
# Migrations + Alembic config travel with the image so the fly
# release_command (`alembic upgrade head`) can resolve everything from
# /app — config, env.py, version scripts, and ``import app.*``.
COPY --chown=app:app apps/api/alembic /app/alembic
COPY --chown=app:app apps/api/alembic.ini /app/alembic.ini

USER app
EXPOSE 8000

CMD ["fastapi", "run", "app/main.py"]
