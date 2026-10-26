import pytest

from crb.db import get_db
from crb.reports import utilisation
from crb.validators import ValidationError
from tests.helpers import make_booking


def report(app, start="2030-01-01", end="2030-01-31"):
    with app.app_context():
        return {row["room"]: row for row in utilisation(get_db(), start, end)}


def test_every_room_is_listed_even_without_bookings(app):
    rows = report(app)
    assert set(rows) == {"Alpha", "Beta", "Gamma", "Delta", "Epsilon"}
    assert rows["Alpha"]["bookings"] == 0
    assert rows["Alpha"]["hours"] == 0


def test_bookings_and_hours_are_counted_per_room(app):
    make_booking(app, start="2030-01-10 10:00", end="2030-01-10 11:30")
    make_booking(app, start="2030-01-11 10:00", end="2030-01-11 11:00")
    make_booking(app, room_id=2, start="2030-01-12 09:00", end="2030-01-12 10:00")
    rows = report(app)
    assert rows["Alpha"]["bookings"] == 2
    assert rows["Alpha"]["hours"] == 2.5
    assert rows["Beta"]["bookings"] == 1
    assert rows["Beta"]["hours"] == 1.0


def test_only_confirmed_bookings_count(app):
    make_booking(app, status="cancelled")
    make_booking(app, room_id=2, status="expired")
    make_booking(app, room_id=3, status="held", hold_expires_at="2030-01-15 09:02:00")
    rows = report(app)
    assert rows["Alpha"]["bookings"] == 0
    assert rows["Beta"]["bookings"] == 0
    assert rows["Gamma"]["bookings"] == 0


def test_date_range_includes_both_end_days(app):
    make_booking(app, start="2030-01-01 08:00", end="2030-01-01 09:00")
    make_booking(app, start="2030-01-31 20:00", end="2030-01-31 21:00")
    make_booking(app, start="2030-02-01 08:00", end="2030-02-01 09:00")
    make_booking(app, start="2029-12-31 08:00", end="2029-12-31 09:00")
    assert report(app)["Alpha"]["bookings"] == 2


def test_end_before_start_is_rejected(app):
    with app.app_context():
        with pytest.raises(ValidationError):
            utilisation(get_db(), "2030-02-01", "2030-01-01")


def test_bad_date_is_rejected(app):
    with app.app_context():
        with pytest.raises(ValidationError):
            utilisation(get_db(), "soon", "2030-01-01")