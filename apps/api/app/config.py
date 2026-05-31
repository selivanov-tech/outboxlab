from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "ci", "production"]
LlmProvider = Literal["anthropic", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str
    api_domain: str
    app_env: AppEnv
    git_sha: str = "dev"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    gmail_user_email: str = ""
    mailbox_workspace_id: str = ""
    poll_interval_seconds: int = 15
    poll_jitter_seconds: int = 5
    llm_enabled: bool = True
    llm_provider: LlmProvider = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_scheme(cls, v: str) -> str:
        return v.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _lowercase_provider(cls, v: str) -> str:
        return v.lower() if isinstance(v, str) else v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def resolve_workspace_id() -> UUID:
    raw = get_settings().mailbox_workspace_id
    if not raw:
        raise RuntimeError("MAILBOX_WORKSPACE_ID is not set")
    return UUID(raw)
