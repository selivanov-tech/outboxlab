from app.config import Settings
from app.entrypoints.worker import drains_send_jobs


def _settings(sender_impl: str) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://x:x@x/x",
        api_domain="localhost",
        app_env="local",
        sender_impl=sender_impl,  # pyright: ignore[reportArgumentType]
    )


def test_the_python_worker_drains_send_jobs_by_default() -> None:
    assert drains_send_jobs(_settings("python"))


def test_the_python_worker_leaves_send_jobs_to_the_go_sender() -> None:
    assert not drains_send_jobs(_settings("go"))
