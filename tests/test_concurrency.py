"""CRB-F-020: many people booking the same slot at once - exactly one wins (SQLite and Postgres)."""
from concurrent.futures import ThreadPoolExecutor

from crb.booking_service import BookingError, create_booking
from crb.db import get_db


def try_to_book(app, user_id):
    with app.app_context():
        try:
            create_booking(get_db(), user_id, 1, "2031-05-05 10:00", "2031-05-05 11:00")
            return True
        except BookingError:
            return False


def test_only_one_of_many_simultaneous_bookings_succeeds(app):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda n: try_to_book(app, 1 + n % 3), range(8)))
    assert results.count(True) == 1
    with app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'"
        ).fetchone()[0]
    assert count == 1
