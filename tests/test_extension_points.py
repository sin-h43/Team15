from jinja2 import ChoiceLoader, DictLoader

from tests.helpers import booking_status, make_booking, make_user


def test_home_page_still_loads_when_no_nav_part_exists(client):
    assert client.get("/").status_code == 200


def test_a_nav_part_file_is_shown_in_the_menu(app, client):
    part = DictLoader({"nav_bookings.html": " | <a href='/x'>Extra link</a>"})
    app.jinja_loader = ChoiceLoader([part, app.jinja_loader])
    assert b"Extra link" in client.get("/").data


def test_message_page_shows_title_and_text(app):
    with app.test_request_context():
        from flask import render_template

        page = render_template("message.html", title="Oops", message="Something went wrong")
    assert "Oops" in page
    assert "Something went wrong" in page


def test_helpers_create_users_and_bookings(app):
    user_id = make_user(app, "employee2", "emp234")
    booking_id = make_booking(app, user_id=user_id)
    assert user_id == 4
    assert booking_status(app, booking_id) == "confirmed"