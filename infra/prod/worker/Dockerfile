# Production image for apps/worker-py — multi-stage, slim runtime.
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.11.15
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /build

# Step 3: COPY apps/worker-py/pyproject.toml apps/worker-py/uv.lock ./
# Step 3: RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app

WORKDIR /app
USER app

# Step 3 entrypoint: python -m app.main
CMD ["sh", "-c", "echo 'prod worker placeholder — wire on Step 3'; exec tail -f /dev/null"]
