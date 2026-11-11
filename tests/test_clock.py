"""The app's clock follows CRB_TIMEZONE, so a UTC server still uses the users' local time."""
from datetime import datetime, timedelta

import pytest

from crb.clock import local_now


def test_timezone_setting_shifts_now(monkeypatch):
    monkeypatch.setenv("CRB_TIMEZONE", "UTC")
    utc = local_now()
    monkeypatch.setenv("CRB_TIMEZONE", "Asia/Kolkata")
    india = local_now()
    gap = india - utc
    assert timedelta(hours=5, minutes=29) < gap < timedelta(hours=5, minutes=31)
    assert india.tzinfo is None


def test_without_a_setting_the_machine_clock_is_used(monkeypatch):
    monkeypatch.delenv("CRB_TIMEZONE", raising=False)
    assert abs(local_now() - datetime.now()) < timedelta(seconds=2)


def test_an_unknown_timezone_name_is_refused(monkeypatch):
    monkeypatch.setenv("CRB_TIMEZONE", "Mars/Olympus")
    with pytest.raises(RuntimeError, match="CRB_TIMEZONE"):
        local_now()


def test_past_check_uses_the_configured_zone(app, monkeypatch):
    """With the clock at India time, a booking 1 hour from India-now is in the future."""
    from crb.booking_service import create_booking
    from crb.db import get_db

    monkeypatch.setenv("CRB_TIMEZONE", "Asia/Kolkata")
    start = (local_now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    end = (local_now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    with app.app_context():
        assert create_booking(get_db(), 1, 1, start, end) > 0
