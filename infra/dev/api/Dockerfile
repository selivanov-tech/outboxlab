FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
# Venv lives outside the bind-mounted source dir at /opt/venv. Two reasons:
# (1) avoid Docker's nested-mount visibility bug when a named volume sits inside
# a bind mount, and (2) bake the venv into the image so PyCharm's "On Docker"
# interpreter can probe /opt/venv/bin/python without extra volume gymnastics.
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.11.17
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Bake the venv into the image. uv sync runs from /tmp/build (with a copy of
# pyproject + lock) so /app stays clean for the runtime bind mount. After this,
# `outboxlab-api` ships with a populated /opt/venv — `pyproject` edits require
# `make rebuild` to pick up new deps, which is fine for the cadence here.
WORKDIR /tmp/build
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen

WORKDIR /app

# Source is bind-mounted from apps/api/. CMD re-runs uv sync as a no-op when
# the lock matches what was baked into the image; updates the venv if it
# doesn't (e.g. after `uv add` without a rebuild).
CMD ["sh", "-c", "uv sync && exec uv run fastapi dev app/main.py --host 0.0.0.0"]
