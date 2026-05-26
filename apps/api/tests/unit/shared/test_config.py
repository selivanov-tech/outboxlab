import pytest

from app.config import Settings


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        api_domain="api.test.local",
        app_env="ci",
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "postgresql://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        (
            "postgres://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        (
            "postgresql+asyncpg://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
    ],
)
def test_database_url_scheme_is_normalized_to_asyncpg(raw: str, expected: str) -> None:
    assert _settings(raw).database_url == expected


def test_database_url_with_password_containing_scheme_only_rewrites_prefix() -> None:
    raw = "postgresql://user:postgresql://@host:5432/db"
    expected = "postgresql+asyncpg://user:postgresql://@host:5432/db"
    assert _settings(raw).database_url == expected
