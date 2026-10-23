from flask import Blueprint, abort, render_template, session

from crb.bookings_view import booking_code
from crb.booking_service import get_booking
from crb.db import get_db
from crb.guards import login_required
from crb.rooms_repo import get_room

bp = Blueprint("bookings_view", __name__)


def can_manage(booking, user_id, role):
    """The owner and any admin may change a booking."""
    return booking["user_id"] == user_id or role == "admin"


def can_view(db, booking, user_id, role):
    """The owner, an admin, an auditor or an invited attendee may look at a booking."""
    if can_manage(booking, user_id, role) or role == "auditor":
        return True
    invited = db.execute(
        "SELECT 1 FROM attendees WHERE booking_id = ? AND user_id = ?", (booking["id"], user_id)
    ).fetchone()
    return invited is not None


@bp.route("/bookings/<int:booking_id>")
@login_required
def booking_page(booking_id):
    db = get_db()
    booking = get_booking(db, booking_id)
    if booking is None:
        abort(404)
    user_id, role = session["user_id"], session["role"]
    if not can_view(db, booking, user_id, role):
        abort(403)
    owner = db.execute("SELECT username FROM users WHERE id = ?", (booking["user_id"],)).fetchone()
    return render_template(
        "booking.html",
        booking=booking,
        room=get_room(db, booking["room_id"]),
        owner=owner["username"],
        code=booking_code(booking_id),
        can_manage=can_manage(booking, user_id, role),
    )


@bp.route("/my-bookings")
@login_required
def my_bookings():
    rows = get_db().execute(
        "SELECT b.*, r.name AS room_name FROM bookings b JOIN rooms r ON r.id = b.room_id "
        "WHERE b.user_id = ? AND b.status != 'expired' ORDER BY b.start_time",
        (session["user_id"],),
    ).fetchall()
    bookings = [{"row": row, "code": booking_code(row["id"])} for row in rows]
    return render_template("my_bookings.html", bookings=bookings)
