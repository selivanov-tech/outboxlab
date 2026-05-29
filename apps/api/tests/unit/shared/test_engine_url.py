from app.shared.infrastructure.db.engine import asyncpg_url_and_connect_args


def test_neon_url_strips_libpq_params_and_maps_sslmode_to_ssl():
    url, connect_args = asyncpg_url_and_connect_args(
        "postgresql+asyncpg://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    )

    assert connect_args == {"ssl": "require"}
    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query


def test_local_url_without_sslmode_passes_no_ssl_arg():
    url, connect_args = asyncpg_url_and_connect_args(
        "postgresql+asyncpg://outboxlab:outboxlab@localhost:5432/outboxlab"
    )

    assert connect_args == {}
    assert url.host == "localhost"
