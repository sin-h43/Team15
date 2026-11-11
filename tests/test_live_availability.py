"""Phase 4: availability that changes live (polling endpoint, hold countdown)."""
from datetime import datetime, timedelta

from crb.db import get_db
from crb.holds import place_hold
from tests.helpers import make_booking, signed_in

QUERY = "/rooms/search?date=2031-06-03&start=10:00&end=11:00&capacity=1&format=json"


def room_ids(client):
    return [room["roomId"] for room in client.get(QUERY).get_json()]


def test_a_room_disappears_from_the_live_results_when_someone_books_it(app):
    client = signed_in(app, "employee1", "emp123")
    assert 1 in room_ids(client)
    make_booking(app, room_id=1, user_id=2, start="2031-06-03 10:00", end="2031-06-03 11:00")
    assert 1 not in room_ids(client)


def test_a_held_room_is_hidden_then_comes_back_when_the_hold_runs_out(app):
    client = signed_in(app, "employee1", "emp123")
    long_ago = datetime.now() - timedelta(minutes=10)
    with app.app_context():
        place_hold(get_db(), 2, 1, "2031-06-03 10:00", "2031-06-03 11:00", now=datetime.now())
    assert 1 not in room_ids(client)
    with app.app_context():
        get_db().execute("UPDATE bookings SET hold_expires_at = ?", (long_ago.strftime("%Y-%m-%d %H:%M:%S"),))
        get_db().commit()
    assert 1 in room_ids(client)


def test_a_cancelled_booking_frees_the_room_again(app):
    booking_id = make_booking(app, room_id=1, start="2031-06-03 10:00", end="2031-06-03 11:00")
    client = signed_in(app, "employee1", "emp123")
    assert 1 not in room_ids(client)
    client.post(f"/bookings/{booking_id}/cancel")
    assert 1 in room_ids(client)


def test_search_page_tells_the_browser_what_to_poll(app):
    page = signed_in(app, "employee1", "emp123").get(
        "/rooms/search?date=2031-06-03&start=10:00&end=11:00"
    ).get_data(as_text=True)
    assert 'id="live-results"' in page and "live.js" in page


def test_booking_page_shows_hold_countdown_and_expires_stale_holds(app):
    client = signed_in(app, "employee1", "emp123")
    with app.app_context():
        booking_id = place_hold(get_db(), 1, 1, "2031-06-03 10:00", "2031-06-03 11:00")
    page = client.get(f"/bookings/{booking_id}").get_data(as_text=True)
    seconds = int(page.split('id="hold-timer" data-seconds="')[1].split('"')[0])
    assert 100 <= seconds <= 120
    with app.app_context():
        get_db().execute("UPDATE bookings SET hold_expires_at = '2000-01-01 00:00:00'")
        get_db().commit()
    stale = client.get(f"/bookings/{booking_id}").get_data(as_text=True)
    assert "hold-timer" not in stale and "expired" in stale
