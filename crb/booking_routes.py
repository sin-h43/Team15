from flask import Blueprint, abort, redirect, render_template, request, session

from crb.booking_service import BookingError, NotFound
from crb.db import get_db
from crb.guards import login_required
from crb.holds import confirm_hold, place_hold
from crb.rooms_repo import get_room
from crb.validators import ValidationError, parse_range
from crb.notifications import notify_booking_created

bp = Blueprint("booking", __name__)


def typed_values():
    """What the user typed (or the search form passed on), so the form can be shown again."""
    return {
        "date": request.values.get("date", ""),
        "start": request.values.get("start", ""),
        "end": request.values.get("end", ""),
    }


@bp.route("/rooms/<int:room_id>/book", methods=["GET", "POST"])
@login_required
def book_room(room_id):
    """Step 1 of checkout: hold the room for 2 minutes (CRB-F-021)."""
    db = get_db()
    room = get_room(db, room_id)
    if room is None or not room["active"]:
        abort(404)
    if request.method == "GET":
        return render_template("book.html", room=room, values=typed_values(), error=None)

    try:
        start, end = parse_range(
            request.form.get("date"), request.form.get("start"), request.form.get("end")
        )
        booking_id = place_hold(db, session["user_id"], room_id, start, end)
    except ValidationError as problem:
        return render_template("book.html", room=room, values=typed_values(), error=str(problem)), 400
    except BookingError as problem:
        return render_template("book.html", room=room, values=typed_values(), error=str(problem)), 409
    return redirect("/bookings/" + str(booking_id))


@bp.route("/bookings/<int:booking_id>/confirm", methods=["POST"])
@login_required
def confirm(booking_id):
    """Step 2 of checkout: turn the hold into a confirmed booking."""
    db = get_db()
    try:
        newly_confirmed = confirm_hold(db, booking_id, session["user_id"])
    except NotFound:
        abort(404)
    except BookingError as problem:
        return render_template("message.html", title="Could not confirm", message=str(problem)), 409
    # HOOK-AFTER-CONFIRM
    from crb.notifications import notify_booking_created
    if newly_confirmed:
        notify_booking_created(db, booking_id)
    return redirect("/bookings/" + str(booking_id))