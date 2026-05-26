from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(tz=UTC)
