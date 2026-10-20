"""Booking creation with conflict prevention (US-14 / CRB-F-020)."""

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from crb.bookings_repo import (
    BookingConflict,
    RoomUnavailable,
    create_booking,
    get_booking,
)
from crb.guards import login_required
from crb.rooms_repo import get_room
from crb.validators import ValidationError, parse_int, parse_range

booking_bp = Blueprint("bookings", __name__)


@booking_bp.route("/bookings/new", methods=["GET"])
@login_required
def new_booking_form():
    room_id = request.args.get("room_id", "")
    room = get_room(int(room_id)) if room_id.isdigit() else None
    return render_template(
        "booking_form.html",
        room=room,
        values=request.args,
        error=None,
    )


@booking_bp.route("/bookings", methods=["POST"])
@login_required
def create_booking_route():
    wants_json = request.is_json or request.path.startswith("/api/")
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}

    try:
        room_id = parse_int(data.get("room_id"), "Room ID")
        start_time, end_time = parse_range(
            data.get("date", ""), data.get("start", ""), data.get("end", "")
        )
        booking_id = create_booking(
            room_id, session["user_id"], start_time, end_time
        )
    except ValidationError as error:
        return _failure(str(error), 400, data, wants_json)
    except BookingConflict as error:
        return _failure(str(error), 409, data, wants_json)
    except RoomUnavailable as error:
        return _failure(str(error), 409, data, wants_json)

    if wants_json:
        return jsonify({"booking": get_booking(booking_id)}), 201
    return redirect(url_for("bookings.confirmation", booking_id=booking_id))


@booking_bp.route("/bookings/<int:booking_id>")
@login_required
def confirmation(booking_id):
    booking = get_booking(booking_id)
    if booking is None:
        abort(404)
    if booking["user_id"] != session["user_id"] and session.get("role") != "admin":
        abort(403)
    return render_template(
        "booking_confirmation.html",
        booking=booking,
        room=get_room(booking["room_id"]),
    )


def _failure(message, status, data, wants_json):
    if wants_json:
        return jsonify({"error": message}), status
    room_id = str(data.get("room_id") or "")
    room = get_room(int(room_id)) if room_id.isdigit() else None
    return (
        render_template("booking_form.html", room=room, values=data, error=message),
        status,
    )