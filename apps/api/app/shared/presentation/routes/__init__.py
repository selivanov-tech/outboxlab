from app.shared.presentation.routes.debug import router as debug_router
from app.shared.presentation.routes.health import router as health_router
from app.shared.presentation.routes.version import router as version_router

__all__ = ["debug_router", "health_router", "version_router"]
