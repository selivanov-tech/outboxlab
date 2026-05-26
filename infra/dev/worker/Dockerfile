FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.11.15
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Bake the venv into the image. Build context is the repo root; uv sync
# runs in /tmp/build so /app stays clean for the dev bind mount.
WORKDIR /tmp/build
COPY apps/worker-py/pyproject.toml apps/worker-py/uv.lock* ./
RUN uv sync

WORKDIR /app

CMD ["sh", "-c", "uv sync && exec uv run python main.py"]
