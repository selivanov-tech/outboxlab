# The engine fixture is function-scoped because asyncpg corrupts its
# protocol state when an AsyncEngine is reused across event loops, and
# pytest-asyncio gives each test its own loop. Do not widen the scope.

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.shared.infrastructure.db.engine import make_engine


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = make_engine()
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async_session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield async_session
        finally:
            await async_session.close()
            if transaction.is_active:
                await transaction.rollback()


pytestmark = pytest.mark.integration
