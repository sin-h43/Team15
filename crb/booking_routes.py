
from flask import Blueprint, abort, redirect, render_template, request, session

from crb.booking_service import BookingError, create_booking
from crb.recurring import create_recurring_bookings
from crb.db import get_db
from crb.guards import login_required
from crb.rooms_repo import get_room
from crb.validators import ValidationError, parse_range

bp = Blueprint("booking", __name__)


def typed_values():
    """Preserve the values entered in the booking form."""
    return {
        "date": request.values.get("date", ""),
        "start": request.values.get("start", ""),
        "end": request.values.get("end", ""),
        "recurrence": request.values.get("recurrence", "none"),
    }


@bp.route("/rooms/<int:room_id>/book", methods=["GET", "POST"])
@login_required
def book_room(room_id):
    db = get_db()
    room = get_room(room_id)
    if room is None or not room["active"]:
        abort(404)

    if request.method == "GET":
        return render_template(
            "book.html", room=room, values=typed_values(), error=None
        )

    try:
        start, end = parse_range(
            request.form.get("date"),
            request.form.get("start"),
            request.form.get("end"),
        )
        recurrence = request.form.get("recurrence", "none")

        if recurrence == "none":
            booking_id = create_booking(
                db, session["user_id"], room_id, start, end
            )
            return redirect("/bookings/" + str(booking_id))

        if recurrence not in ("daily", "weekly"):
            raise ValidationError("Invalid recurrence choice")

        result = create_recurring_bookings(
            db, session["user_id"], room_id, start, end, recurrence
        )

        if not result["booking_ids"]:
            message = (
                "No occurrences were booked. Conflicting dates: "
                + ", ".join(result["conflicts"])
            )
            return render_template(
                "book.html", room=room, values=typed_values(), error=message
            ), 409

        return render_template(
            "recurring_result.html", room=room, result=result
        )

    except ValidationError as problem:
        return render_template(
            "book.html", room=room, values=typed_values(), error=str(problem)
        ), 400
    except BookingError as problem:
        return render_template(
            "book.html", room=room, values=typed_values(), error=str(problem)
        ), 409
