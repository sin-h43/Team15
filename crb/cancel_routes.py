from flask import Blueprint, abort, redirect, render_template, session

from crb.audit import log_action
from crb.booking_code import booking_code
from crb.booking_service import BookingError, NotAllowed, NotFound
from crb.cancellation import cancel_booking
from crb.db import get_db
from crb.guards import login_required

bp = Blueprint("cancel_routes", __name__)


@bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id):
    db = get_db()
    try:
        cancel_booking(db, booking_id, session["user_id"], session["role"])
    except NotFound:
        abort(404)
    except NotAllowed:
        abort(403)
    except BookingError as problem:
        return render_template("message.html", title="Cannot cancel", message=str(problem)), 409

    if session["role"] == "admin":
        log_action(db, session["username"], "BOOKING_CANCELLED", "booking " + booking_code(booking_id))
    # HOOK-AFTER-CANCEL
    return redirect("/bookings/" + str(booking_id))
