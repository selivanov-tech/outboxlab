from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.contexts.campaign.presentation.routes import (
    campaigns_router,
    internal_send_jobs_router,
)
from app.contexts.identity.infrastructure.api_key_resolver import (
    resolve_workspace_by_api_key,
)
from app.contexts.identity.presentation.routes import workspaces_router
from app.contexts.messaging.presentation.routes import messaging_router
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.presentation.middleware import WorkspaceContextMiddleware
from app.shared.presentation.routes import debug_router, health_router, version_router
from app.shared.presentation.viewer.app import viewer_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await dispose_engine()


def create_app(settings: Settings) -> FastAPI:
    production = settings.app_env == "production"
    app = FastAPI(title="OutboxLab API", lifespan=lifespan)
    app.add_middleware(
        WorkspaceContextMiddleware,
        resolve_api_key=resolve_workspace_by_api_key,
        accept_workspace_header=not production,
    )
    app.include_router(health_router)
    app.include_router(version_router)
    app.include_router(workspaces_router)
    app.include_router(campaigns_router)
    app.include_router(debug_router)
    app.mount("/viewer", viewer_app(), name="viewer")
    # /send-test-email sends one-off mail outside any campaign; it stays out of
    # production even behind an API key.
    if not production:
        app.include_router(messaging_router)
    if not production and settings.internal_api_token:
        app.include_router(internal_send_jobs_router)
    return app


app = create_app(get_settings())
