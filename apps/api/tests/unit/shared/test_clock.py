from datetime import UTC, datetime, timedelta, timezone

from app.shared.util.clock import start_of_utc_day


def test_start_of_utc_day_uses_the_utc_calendar_day() -> None:
    late_evening_west = datetime(
        2026, 9, 12, 22, 30, tzinfo=timezone(timedelta(hours=-5))
    )

    assert start_of_utc_day(late_evening_west) == datetime(2026, 9, 13, tzinfo=UTC)
