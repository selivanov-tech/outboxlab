import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.shared.infrastructure.db.base import Base
from app.shared.infrastructure.db.engine import asyncpg_url_and_connect_args

# Imports below are load-bearing: importing a model module registers its
# tables on Base.metadata. Do not "clean up" these as unused.
from app.campaign.infrastructure.db import models as _campaign_models  # noqa: F401
from app.identity.infrastructure.db import models as _identity_models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


async def _run_migrations() -> None:
    def run_sync(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

    url, connect_args = asyncpg_url_and_connect_args(get_settings().database_url)
    engine = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with engine.connect() as connection:
        await connection.run_sync(run_sync)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported")
asyncio.run(_run_migrations())
