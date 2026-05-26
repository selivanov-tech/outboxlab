from contextvars import ContextVar
from uuid import UUID

current_workspace_id: ContextVar[UUID | None] = ContextVar(
    "current_workspace_id", default=None
)
