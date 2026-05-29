import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.shared.infrastructure.db.base import Base

# Imports below are load-bearing: importing a model module registers its
# tables on Base.metadata. Do not "clean up" these as unused.
from app.campaign.infrastructure.db import models as _campaign_models  # noqa: F401
from app.identity.infrastructure.db import models as _identity_models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url)


async def _run_migrations() -> None:
    def run_sync(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(run_sync)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported")
asyncio.run(_run_migrations())
