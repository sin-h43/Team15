
from datetime import datetime

import pytest

from crb.booking_service import BookingError
from crb.cancellation import cancel_occurrence, edit_occurrence
from crb.db import get_db
from tests.helpers import make_booking


NOW = datetime(2030, 1, 1, 9, 0)


def test_cancel_occurrence_does_not_cancel_other_series_bookings(app):
    with app.app_context():
        db = get_db()
        first = make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00",
                             series_id=10)
        second = make_booking(app, start="2030-01-16 10:00", end="2030-01-16 11:00",
                              series_id=10)

        cancel_occurrence(db, first, 1, "employee")

        rows = db.execute(
            "SELECT id, status FROM bookings WHERE series_id = 10 ORDER BY id"
        ).fetchall()
        assert rows[0]["status"] == "cancelled"
        assert rows[1]["status"] == "confirmed"


def test_edit_occurrence_changes_only_selected_booking(app):
    with app.app_context():
        db = get_db()
        first = make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00",
                             series_id=11)
        second = make_booking(app, start="2030-01-16 10:00", end="2030-01-16 11:00",
                              series_id=11)

        edit_occurrence(
            db, first, 1, "employee",
            "2030-01-15 12:00", "2030-01-15 13:00", now=NOW,
        )

        first_row = db.execute(
            "SELECT * FROM bookings WHERE id = ?", (first,)
        ).fetchone()
        second_row = db.execute(
            "SELECT * FROM bookings WHERE id = ?", (second,)
        ).fetchone()

        assert first_row["start_time"] == "2030-01-15 12:00"
        assert second_row["start_time"] == "2030-01-16 10:00"


def test_edit_occurrence_rejects_conflict(app):
    with app.app_context():
        db = get_db()
        first = make_booking(app, start="2030-01-15 10:00", end="2030-01-15 11:00",
                             series_id=12)
        make_booking(app, start="2030-01-15 12:00", end="2030-01-15 13:00")

        with pytest.raises(BookingError):
            edit_occurrence(
                db, first, 1, "employee",
                "2030-01-15 12:30", "2030-01-15 13:30", now=NOW,
            )

        row = db.execute("SELECT * FROM bookings WHERE id = ?", (first,)).fetchone()
        assert row["start_time"] == "2030-01-15 10:00"
