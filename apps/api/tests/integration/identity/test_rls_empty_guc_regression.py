from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_empty_workspace_guc_does_not_crash_tenant_query(
    session: AsyncSession,
) -> None:
    await session.execute(text("SET LOCAL ROLE outboxlab_app"))
    await session.execute(text("SELECT set_config('app.workspace_id', '', true)"))

    result = await session.execute(text("SELECT COUNT(*) FROM campaigns"))
    assert result.scalar_one() == 0
