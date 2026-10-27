
from datetime import datetime

import pytest

from crb.booking_service import BookingError
from crb.db import get_db
from crb.recurring import create_recurring_bookings
from tests.helpers import make_booking


NOW = datetime(2030, 1, 1, 9, 0)


def test_daily_recurrence_creates_occurrences(app):
    with app.app_context():
        db = get_db()
        result = create_recurring_bookings(
            db, 1, 1,
            "2030-01-15 10:00", "2030-01-15 11:00",
            "daily", now=NOW,
        )

        assert len(result["booking_ids"]) > 1
        assert result["conflicts"] == []

        rows = db.execute(
            "SELECT * FROM bookings WHERE series_id = ? ORDER BY start_time",
            (result["series_id"],),
        ).fetchall()

        assert rows[0]["start_time"] == "2030-01-15 10:00"
        assert rows[1]["start_time"] == "2030-01-16 10:00"


def test_weekly_recurrence_creates_seven_day_intervals(app):
    with app.app_context():
        db = get_db()
        result = create_recurring_bookings(
            db, 1, 1,
            "2030-01-15 10:00", "2030-01-15 11:00",
            "weekly", now=NOW,
        )

        rows = db.execute(
            "SELECT * FROM bookings WHERE series_id = ? ORDER BY start_time",
            (result["series_id"],),
        ).fetchall()

        assert len(rows) > 1
        assert rows[0]["start_time"] == "2030-01-15 10:00"
        assert rows[1]["start_time"] == "2030-01-22 10:00"


def test_conflicting_occurrence_is_reported_and_skipped(app):
    make_booking(
        app,
        start="2030-01-16 10:00",
        end="2030-01-16 11:00",
    )

    with app.app_context():
        db = get_db()
        result = create_recurring_bookings(
            db, 1, 1,
            "2030-01-15 10:00", "2030-01-15 11:00",
            "daily", now=NOW,
        )

        assert "2030-01-16 10:00" in result["conflicts"]
        assert len(result["booking_ids"]) > 0

        conflict_count = db.execute(
            "SELECT COUNT(*) FROM bookings "
            "WHERE room_id = 1 AND start_time = '2030-01-16 10:00' "
            "AND status = 'confirmed'"
        ).fetchone()[0]

        assert conflict_count == 1


def test_invalid_recurrence_is_rejected(app):
    with app.app_context():
        with pytest.raises(BookingError):
            create_recurring_bookings(
                get_db(), 1, 1,
                "2030-01-15 10:00", "2030-01-15 11:00",
                "monthly", now=NOW,
            )


def test_start_beyond_90_days_is_rejected(app):
    with app.app_context():
        with pytest.raises(BookingError):
            create_recurring_bookings(
                get_db(), 1, 1,
                "2030-04-10 10:00", "2030-04-10 11:00",
                "daily", now=NOW,
            )
