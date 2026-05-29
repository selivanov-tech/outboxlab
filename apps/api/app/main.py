from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.identity.presentation.routes import workspaces_router
from app.shared.infrastructure.db.engine import dispose_engine
from app.shared.presentation.middleware import WorkspaceContextMiddleware
from app.shared.presentation.routes import debug_router, health_router, version_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await dispose_engine()


app = FastAPI(title="OutboxLab API", lifespan=lifespan)
app.add_middleware(WorkspaceContextMiddleware)
app.include_router(health_router)
app.include_router(version_router)
app.include_router(workspaces_router)
if get_settings().app_env != "production":
    app.include_router(debug_router)
