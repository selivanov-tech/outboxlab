from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.context import current_workspace_id
from app.shared.infrastructure.db.engine import get_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session, session.begin():
        ws_id = current_workspace_id.get()
        if ws_id is not None:
            # set_config(..., is_local=true) is the only SET LOCAL form that accepts bind parameters.
            await session.execute(
                text("SELECT set_config('app.workspace_id', :ws_id, true)"),
                {"ws_id": str(ws_id)},
            )
        yield session
