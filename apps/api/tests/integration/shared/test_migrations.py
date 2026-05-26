from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_EXPECTED_TABLES = {
    "workspaces",
    "campaigns",
}

_RLS_FORCED_TABLES = {
    "campaigns",
}


async def test_all_expected_tables_exist(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname='public' AND tablename != 'alembic_version'"
        )
    )
    tables = {row[0] for row in result}
    assert _EXPECTED_TABLES.issubset(tables), (
        f"missing tables: {_EXPECTED_TABLES - tables}"
    )


async def test_rls_forced_on_tenant_tables(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind='r'"
        )
    )
    flags = {row[0]: (row[1], row[2]) for row in result}
    for table in _RLS_FORCED_TABLES:
        assert flags[table] == (True, True), (
            f"{table} expected RLS=True FORCE=True, got {flags[table]}"
        )
    assert flags["workspaces"] == (False, False)
