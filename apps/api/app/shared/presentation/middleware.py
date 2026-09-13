from collections.abc import Awaitable, Callable
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.shared.application.context import current_workspace_id

WORKSPACE_HEADER = "X-Workspace-Id"
_BEARER_PREFIX = "bearer "

ApiKeyResolver = Callable[[str], Awaitable[UUID | None]]


class _RejectedCredentialsError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class WorkspaceContextMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        resolve_api_key: ApiKeyResolver,
        accept_workspace_header: bool,
    ) -> None:
        super().__init__(app)
        self._resolve_api_key = resolve_api_key
        self._accept_workspace_header = accept_workspace_header

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            workspace_id = await self._workspace_id(request)
        except _RejectedCredentialsError as rejected:
            return JSONResponse(
                status_code=rejected.status_code, content={"detail": rejected.detail}
            )
        token = (
            current_workspace_id.set(workspace_id) if workspace_id is not None else None
        )
        try:
            return await call_next(request)
        finally:
            if token is not None:
                current_workspace_id.reset(token)

    async def _workspace_id(self, request: Request) -> UUID | None:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith(_BEARER_PREFIX):
            workspace_id = await self._resolve_api_key(
                authorization[len(_BEARER_PREFIX) :]
            )
            if workspace_id is None:
                raise _RejectedCredentialsError(401, "Invalid API key")
            return workspace_id

        raw = request.headers.get(WORKSPACE_HEADER)
        if not raw:
            return None
        if not self._accept_workspace_header:
            raise _RejectedCredentialsError(
                401, f"{WORKSPACE_HEADER} is not accepted here; use an API key"
            )
        try:
            return UUID(raw)
        except ValueError:
            raise _RejectedCredentialsError(400, f"Malformed {WORKSPACE_HEADER} header")
