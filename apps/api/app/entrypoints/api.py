from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastmcp.server.http import StarletteWithLifespan

from app.config import Settings, get_settings
from app.contexts.campaign.presentation.routes import (
    campaigns_router,
    internal_send_jobs_router,
)
from app.contexts.identity.infrastructure.api_key_resolver import (
    resolve_workspace_by_api_key,
)
from app.contexts.identity.presentation.routes import workspaces_router
from app.contexts.mailbox.presentation.routes import mailboxes_router
from app.contexts.messaging.presentation.routes import messaging_router
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.presentation.http_metrics import HttpMetricsMiddleware
from app.shared.presentation.mcp import build_mcp_server
from app.shared.presentation.middleware import (
    ApiKeyResolver,
    WorkspaceContextMiddleware,
)
from app.shared.presentation.routes import (
    debug_router,
    health_router,
    metrics_router,
    version_router,
)
from app.shared.presentation.viewer.app import viewer_app


def _lifespan(
    mcp_app: StarletteWithLifespan,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with mcp_app.lifespan(app):
            try:
                yield
            finally:
                await dispose_engine()

    return lifespan


def create_app(
    settings: Settings,
    resolve_api_key: ApiKeyResolver = resolve_workspace_by_api_key,
) -> FastAPI:
    production = settings.app_env == "production"
    app = FastAPI(title="OutboxLab API")
    app.add_middleware(
        WorkspaceContextMiddleware,
        resolve_api_key=resolve_api_key,
        accept_workspace_header=not production,
    )
    app.add_middleware(HttpMetricsMiddleware)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(version_router)
    app.include_router(workspaces_router)
    app.include_router(campaigns_router)
    app.include_router(mailboxes_router)
    app.include_router(debug_router)
    # /send-test-email sends one-off mail outside any campaign; it stays out of
    # production even behind an API key.
    if not production:
        app.include_router(messaging_router)
    if not production and settings.internal_api_token:
        app.include_router(internal_send_jobs_router)

    mcp_app = build_mcp_server(app).http_app(path="/")
    app.mount("/mcp", mcp_app, name="mcp")
    app.mount("/viewer", viewer_app(), name="viewer")
    app.router.lifespan_context = _lifespan(mcp_app)
    return app


app = create_app(get_settings())
