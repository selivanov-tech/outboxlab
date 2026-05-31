from uuid import UUID

from fastapi import HTTPException

from app.shared.application.context import current_workspace_id


async def require_workspace() -> UUID:
    workspace_id = current_workspace_id.get()
    if workspace_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Workspace-Id header")
    return workspace_id
