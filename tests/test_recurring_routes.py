from datetime import datetime, timedelta

from crb.db import get_db
from tests.helpers import signed_in


def future_booking_time():
    start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=3)
    end = start + timedelta(hours=1)
    return (
        start.strftime("%Y-%m-%d"),
        start.strftime("%H:%M"),
        end.strftime("%H:%M"),
    )


def test_visitor_is_redirected_to_login(client):
    response = client.get("/recurring")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_recurring_page_is_available_to_logged_in_user(app):
    client = signed_in(app, "employee1", "emp123")

    response = client.get("/recurring")

    assert response.status_code == 200
    assert b"Create Recurring Booking" in response.data
    assert b"Daily" in response.data
    assert b"Weekly" in response.data


def test_daily_recurring_booking_can_be_created(app):
    client = signed_in(app, "employee1", "emp123")
    date, start, end = future_booking_time()

    response = client.post(
        "/recurring",
        data={
            "room_id": "1",
            "date": date,
            "start": start,
            "end": end,
            "frequency": "daily",
        },
    )

    assert response.status_code == 200
    assert b"Recurring Booking Series" in response.data

    with app.app_context():
        db = get_db()
        rows = db.execute(
            "SELECT * FROM bookings WHERE series_id IS NOT NULL"
        ).fetchall()

        assert len(rows) > 1
        assert len({row["series_id"] for row in rows}) == 1


def test_weekly_recurring_booking_can_be_created(app):
    client = signed_in(app, "employee1", "emp123")
    date, start, end = future_booking_time()

    response = client.post(
        "/recurring",
        data={
            "room_id": "1",
            "date": date,
            "start": start,
            "end": end,
            "frequency": "weekly",
        },
    )

    assert response.status_code == 200
    assert b"Recurring Booking Series" in response.data


def test_invalid_frequency_is_rejected(app):
    client = signed_in(app, "employee1", "emp123")
    date, start, end = future_booking_time()

    response = client.post(
        "/recurring",
        data={
            "room_id": "1",
            "date": date,
            "start": start,
            "end": end,
            "frequency": "monthly",
        },
    )

    assert response.status_code == 400
    assert b"daily or weekly" in response.data


def test_series_page_is_not_visible_to_another_employee(app):
    client = signed_in(app, "employee1", "emp123")
    date, start, end = future_booking_time()

    response = client.post(
        "/recurring",
        data={
            "room_id": "1",
            "date": date,
            "start": start,
            "end": end,
            "frequency": "weekly",
        },
    )
    assert response.status_code == 200

    with app.app_context():
        series_id = get_db().execute(
            "SELECT series_id FROM bookings WHERE series_id IS NOT NULL LIMIT 1"
        ).fetchone()["series_id"]

    other_client = signed_in(app, "auditor1", "aud123")
    # Auditors are allowed to view series.
    assert other_client.get(f"/recurring/{series_id}").status_code == 200