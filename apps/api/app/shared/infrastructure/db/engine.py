from sqlalchemy import make_url
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings

# asyncpg rejects libpq-only query params: `sslmode` raises TypeError on connect()
# and `channel_binding` is negotiated automatically with no connect kwarg. Neon's
# connection string ships both, so strip them and map sslmode onto asyncpg's `ssl`.
_LIBPQ_ONLY_QUERY = ("sslmode", "channel_binding")


def asyncpg_url_and_connect_args(database_url: str) -> tuple[URL, dict[str, object]]:
    url = make_url(database_url)
    connect_args: dict[str, object] = {}
    sslmode = url.query.get("sslmode")
    if sslmode:
        connect_args["ssl"] = sslmode[0] if isinstance(sslmode, tuple) else sslmode
    return url.difference_update_query(_LIBPQ_ONLY_QUERY), connect_args


def make_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    url, connect_args = asyncpg_url_and_connect_args(settings.database_url)
    return create_async_engine(
        url,
        echo=settings.app_env == "local",
        pool_pre_ping=True,
        connect_args=connect_args,
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
