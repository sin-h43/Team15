from datetime import datetime

from crb.db import get_db
from crb.hold_cleanup import release_expired_holds
from crb.search import find_rooms
from tests.helpers import booking_status, make_booking

NOW = datetime(2030, 1, 15, 9, 0, 0)
START = "2030-01-15 10:00"
END = "2030-01-15 11:00"


def test_expired_hold_is_released(app):
    booking_id = make_booking(app, status="held", hold_expires_at="2030-01-15 08:58:00")
    with app.app_context():
        assert release_expired_holds(get_db(), NOW) == 1
    assert booking_status(app, booking_id) == "expired"


def test_live_hold_is_kept(app):
    booking_id = make_booking(app, status="held", hold_expires_at="2030-01-15 09:02:00")
    with app.app_context():
        assert release_expired_holds(get_db(), NOW) == 0
    assert booking_status(app, booking_id) == "held"


def test_confirmed_booking_is_never_touched(app):
    booking_id = make_booking(app)
    with app.app_context():
        assert release_expired_holds(get_db(), NOW) == 0
    assert booking_status(app, booking_id) == "confirmed"


def test_search_frees_a_room_whose_hold_ran_out(app):
    booking_id = make_booking(app, status="held", hold_expires_at="2030-01-15 08:58:00")
    with app.app_context():
        names = [room["name"] for room in find_rooms(get_db(), START, END, now=NOW)]
    assert "Alpha" in names
    assert booking_status(app, booking_id) == "expired"


def test_search_does_not_offer_a_room_with_a_live_hold(app):
    make_booking(app, status="held", hold_expires_at="2030-01-15 09:02:00")
    with app.app_context():
        names = [room["name"] for room in find_rooms(get_db(), START, END, now=NOW)]
    assert "Alpha" not in names
    assert "Beta" in names