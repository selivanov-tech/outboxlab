from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.infrastructure.db.models import Workspace as WorkspaceRow
from app.shared.infrastructure.db.engine import get_session_factory

router = APIRouter()


async def _session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


@router.get("/debug/state")
async def state(
    session: Annotated[AsyncSession, Depends(_session)],
) -> dict[str, object]:
    try:
        stmt = select(func.count()).select_from(WorkspaceRow)
        workspace_count = (await session.execute(stmt)).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"db: {exc.__class__.__name__}")
    return {"db": "ok", "workspace_count": int(workspace_count)}
