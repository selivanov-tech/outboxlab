from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.shared.application.context import current_workspace_id

WORKSPACE_HEADER = "X-Workspace-Id"


class WorkspaceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        raw = request.headers.get(WORKSPACE_HEADER)
        token = None
        if raw:
            try:
                token = current_workspace_id.set(UUID(raw))
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Malformed {WORKSPACE_HEADER} header"},
                )
        try:
            return await call_next(request)
        finally:
            if token is not None:
                current_workspace_id.reset(token)
