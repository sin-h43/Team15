from flask import Blueprint, abort, redirect, render_template, request, session


from crb.cancellation import edit_occurrence
from crb.validators import ValidationError, parse_range
from crb.audit import log_action
from crb.booking_code import booking_code
from crb.booking_service import BookingError, NotAllowed, NotFound, get_booking
from crb.cancellation import cancel_booking, cancel_occurrence
from crb.db import get_db
from crb.guards import login_required

bp = Blueprint("cancel_routes", __name__)


@bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id):
    db = get_db()
    existing = get_booking(db, booking_id)
    was_confirmed = existing is not None and existing["status"] == "confirmed"
    try:
        cancel_occurrence(db, booking_id, session["user_id"], session["role"])
    except NotFound:
        abort(404)
    except NotAllowed:
        abort(403)
    except BookingError as problem:
        return render_template("message.html", title="Cannot cancel", message=str(problem)), 409

    if session["role"] == "admin":
        log_action(db, session["username"], "BOOKING_CANCELLED", "booking " + booking_code(booking_id))
    # HOOK-AFTER-CANCEL
    from crb.cancel_notice import notify_booking_cancelled
    if was_confirmed:
        notify_booking_cancelled(db, booking_id)
    return redirect("/bookings/" + str(booking_id))


@bp.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def edit(booking_id):
    db = get_db()

    booking = get_booking(db, booking_id)
    if booking is None:
        abort(404)

    if booking["user_id"] != session["user_id"] and session["role"] != "admin":
        abort(403)

    if request.method == "GET":
        return render_template("edit_booking.html", booking=booking, error=None)

    try:
        start, end = parse_range(
            request.form.get("date"),
            request.form.get("start"),
            request.form.get("end"),
        )
        edit_occurrence(
            db, booking_id, session["user_id"], session["role"], start, end
        )
    except ValidationError as problem:
        return render_template(
            "edit_booking.html", booking=booking, error=str(problem)
        ), 400
    except BookingError as problem:
        return render_template(
            "edit_booking.html", booking=booking, error=str(problem)
        ), 409

    if session["role"] == "admin":
        log_action(db, session["username"], "BOOKING_EDITED", "booking " + booking_code(booking_id))
    from crb.notifications import notify_booking_changed
    notify_booking_changed(db, booking_id)
    return redirect("/bookings/" + str(booking_id))
