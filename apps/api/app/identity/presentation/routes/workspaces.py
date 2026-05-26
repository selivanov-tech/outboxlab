from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.application.queries.get_my_workspace import (
    GetMyWorkspaceHandler,
    WorkspaceNotFoundError,
)
from app.identity.domain.workspace import Workspace
from app.identity.infrastructure.persistence.workspace_repo import WorkspaceRepository
from app.shared.application.context import current_workspace_id
from app.shared.infrastructure.db.session import get_session

router = APIRouter()


def get_my_workspace_handler(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GetMyWorkspaceHandler:
    return GetMyWorkspaceHandler(WorkspaceRepository(session))


@router.get("/workspaces/me", response_model=Workspace)
async def get_my_workspace(
    handler: Annotated[GetMyWorkspaceHandler, Depends(get_my_workspace_handler)],
) -> Workspace:
    ws_id = current_workspace_id.get()
    if ws_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Workspace-Id header")
    try:
        return await handler.execute(ws_id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
