from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.application.queries.get_my_workspace import (
    GetMyWorkspaceHandler,
    WorkspaceNotFoundError,
)
from app.contexts.identity.domain.workspace import Workspace
from app.contexts.identity.infrastructure.persistence.workspace_repo import (
    WorkspaceRepository,
)
from app.shared.infrastructure.db.session import get_session
from app.shared.presentation.dependencies import require_workspace

router = APIRouter()


def get_my_workspace_handler(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GetMyWorkspaceHandler:
    return GetMyWorkspaceHandler(WorkspaceRepository(session))


@router.get("/workspaces/me", response_model=Workspace)
async def get_my_workspace(
    workspace_id: Annotated[UUID, Depends(require_workspace)],
    handler: Annotated[GetMyWorkspaceHandler, Depends(get_my_workspace_handler)],
) -> Workspace:
    try:
        return await handler.execute(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
