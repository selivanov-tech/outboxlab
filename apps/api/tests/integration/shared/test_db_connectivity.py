import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_select_one(session: AsyncSession) -> None:
    result = await session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_set_local_workspace_id_scoped_to_transaction(
    session: AsyncSession,
) -> None:
    ws_id = uuid.uuid7()
    await session.execute(
        text("SELECT set_config('app.workspace_id', :id, true)"),
        {"id": str(ws_id)},
    )
    current = (
        await session.execute(text("SELECT current_setting('app.workspace_id', true)"))
    ).scalar_one()
    assert current == str(ws_id)


async def test_unscoped_session_sees_no_app_workspace_id(
    session: AsyncSession,
) -> None:
    current = (
        await session.execute(text("SELECT current_setting('app.workspace_id', true)"))
    ).scalar_one()
    assert current in (None, "")
