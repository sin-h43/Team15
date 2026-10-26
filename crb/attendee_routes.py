from flask import Blueprint, abort, redirect, render_template, request, session

from crb.attendees import AttendeeError, add_attendee, list_attendees
from crb.booking_code import booking_code
from crb.booking_service import get_booking
from crb.bookings_view import can_manage
from crb.db import get_db
from crb.guards import login_required
from crb.validators import ValidationError, parse_text

bp = Blueprint("attendee_routes", __name__)


@bp.route("/bookings/<int:booking_id>/attendees", methods=["GET", "POST"])
@login_required
def attendees_page(booking_id):
    db = get_db()
    booking = get_booking(db, booking_id)
    if booking is None:
        abort(404)
    if not can_manage(booking, session["user_id"], session["role"]):
        abort(403)

    error = None
    status = 200
    if request.method == "POST":
        try:
            add_attendee(db, booking_id, parse_text(request.form.get("username"), "Username"))
        except (ValidationError, AttendeeError) as problem:
            error = str(problem)
            status = 400
        else:
            return redirect("/bookings/" + str(booking_id) + "/attendees")

    page = render_template(
        "attendees.html",
        booking=booking,
        code=booking_code(booking_id),
        attendees=list_attendees(db, booking_id),
        error=error,
    )
    return page, status