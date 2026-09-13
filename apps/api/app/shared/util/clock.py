from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(tz=UTC)


def start_of_utc_day(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
