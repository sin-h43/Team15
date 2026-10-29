from flask import Blueprint, abort, redirect, render_template, request, session

from crb.booking_code import booking_code
from crb.booking_service import BookingError, NotAllowed, NotFound, get_booking
from crb.bookings_view import can_manage
from crb.db import get_db
from crb.guards import login_required
from crb.reschedule import reschedule_booking
from crb.rooms_repo import list_rooms
from crb.validators import ValidationError, parse_int, parse_range

bp = Blueprint("reschedule_routes", __name__)


def show_form(booking, values, error=None, status=200):
    db = get_db()
    rooms = [room for room in list_rooms(db) if room["active"]]
    page = render_template(
        "reschedule.html", booking=booking, code=booking_code(booking["id"]),
        rooms=rooms, values=values, error=error,
    )
    return page, status


@bp.route("/bookings/<int:booking_id>/reschedule", methods=["GET", "POST"])
@login_required
def reschedule(booking_id):
    db = get_db()
    booking = get_booking(db, booking_id)
    if booking is None:
        abort(404)
    if not can_manage(booking, session["user_id"], session["role"]):
        abort(403)

    if request.method == "GET":
        values = {
            "room_id": booking["room_id"],
            "date": booking["start_time"][:10],
            "start": booking["start_time"][11:16],
            "end": booking["end_time"][11:16],
        }
        return show_form(booking, values)

    values = {
        "room_id": request.form.get("room_id", ""),
        "date": request.form.get("date", ""),
        "start": request.form.get("start", ""),
        "end": request.form.get("end", ""),
    }
    try:
        room_id = parse_int(values["room_id"], "Room")
        start, end = parse_range(values["date"], values["start"], values["end"])
        reschedule_booking(db, booking_id, session["user_id"], session["role"], room_id, start, end)
    except ValidationError as problem:
        return show_form(booking, values, str(problem), 400)
    except NotAllowed:
        abort(403)
    except NotFound:
        abort(404)
    except BookingError as problem:
        return show_form(booking, values, str(problem), 409)
    return redirect("/bookings/" + str(booking_id))