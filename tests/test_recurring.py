
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


def test_series_stops_at_the_chosen_end_date(app):
    with app.app_context():
        result = create_recurring_bookings(
            get_db(), 1, 1, "2030-01-15 10:00", "2030-01-15 11:00", "daily", now=NOW, until="2030-01-19")
    assert len(result["booking_ids"]) == 5          # 15, 16, 17, 18, 19 January


def test_weekly_series_with_end_date(app):
    with app.app_context():
        result = create_recurring_bookings(
            get_db(), 1, 1, "2030-01-15 10:00", "2030-01-15 11:00", "weekly", now=NOW, until="2030-02-05")
    assert len(result["booking_ids"]) == 4          # 15, 22, 29 January and 5 February


def test_end_date_before_the_first_date_is_refused(app):
    with app.app_context():
        with pytest.raises(BookingError, match="before the first date"):
            create_recurring_bookings(
                get_db(), 1, 1, "2030-01-15 10:00", "2030-01-15 11:00", "daily", now=NOW, until="2030-01-10")


def test_end_date_beyond_the_horizon_is_refused(app):
    with app.app_context():
        with pytest.raises(BookingError, match="within the next 90 days"):
            create_recurring_bookings(
                get_db(), 1, 1, "2030-01-15 10:00", "2030-01-15 11:00", "daily", now=NOW, until="2030-06-01")


def test_horizon_is_configurable(app):
    app.config["RECURRING_HORIZON_DAYS"] = 30
    with app.app_context():
        result = create_recurring_bookings(
            get_db(), 1, 1, "2030-01-15 10:00", "2030-01-15 11:00", "daily", now=NOW)
        with pytest.raises(BookingError, match="within the next 30 days"):
            create_recurring_bookings(
                get_db(), 1, 2, "2030-01-15 10:00", "2030-01-15 11:00", "daily", now=NOW, until="2030-03-01")
    # NOW is 1 January 09:00; 30 days ahead is 31 January 09:00, so the last 10:00 slot is 30 January
    assert len(result["booking_ids"]) == 16         # 15..30 January


def test_recurring_page_has_the_end_date_field_and_uses_it(app):
    from datetime import timedelta

    from crb.clock import local_now
    from tests.helpers import signed_in

    first = (local_now() + timedelta(days=2)).date()
    client = signed_in(app, "employee1", "emp123")
    page = client.get("/recurring").get_data(as_text=True)
    assert 'name="until"' in page and "90 days" in page
    response = client.post("/recurring", data={
        "room_id": "1", "date": first.isoformat(), "start": "09:00", "end": "10:00",
        "frequency": "daily", "until": (first + timedelta(days=2)).isoformat()})
    assert response.status_code == 200
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM bookings WHERE series_id IS NOT NULL").fetchone()[0]
    assert count == 3
