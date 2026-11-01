from flask import Blueprint, abort, redirect, render_template, request, session

from crb.booking_service import BookingError
from crb.db import get_db
from crb.guards import login_required
from crb.recurring import create_recurring_bookings
from crb.validators import ValidationError, parse_int, parse_range

bp = Blueprint("recurring", __name__)


@bp.route("/recurring", methods=["GET", "POST"])
@login_required
def recurring_home():
    db = get_db()

    rooms = db.execute(
        "SELECT * FROM rooms WHERE active = 1 ORDER BY name"
    ).fetchall()

    if request.method == "POST":
        try:
            room_id = parse_int(request.form.get("room_id"), "Room")
            start, end = parse_range(
                request.form.get("date"),
                request.form.get("start"),
                request.form.get("end"),
            )
            frequency = request.form.get("frequency", "")

            result = create_recurring_bookings(
                db,
                session["user_id"],
                room_id,
                start,
                end,
                frequency,
            )

            bookings = db.execute(
                "SELECT * FROM bookings WHERE series_id = ? "
                "ORDER BY start_time",
                (result["series_id"],),
            ).fetchall()

            return render_template(
                "series.html",
                series_id=result["series_id"],
                bookings=bookings,
                conflicts=result["conflicts"],
            )

        except (ValidationError, BookingError, ValueError) as problem:
            return render_template(
                "recurring.html",
                rooms=rooms,
                error=str(problem),
                values=request.form,
            ), 400

    return render_template(
        "recurring.html",
        rooms=rooms,
        error=None,
        values={},
    )


@bp.route("/recurring/<int:series_id>")
@login_required
def recurring_series(series_id):
    db = get_db()

    bookings = db.execute(
        "SELECT b.*, r.name AS room_name "
        "FROM bookings b JOIN rooms r ON r.id = b.room_id "
        "WHERE b.series_id = ? ORDER BY b.start_time",
        (series_id,),
    ).fetchall()

    if not bookings:
        abort(404)

    if (
        bookings[0]["user_id"] != session["user_id"]
        and session["role"] != "admin"
        and session["role"] != "auditor"
    ):
        abort(403)

    return render_template(
        "series.html",
        series_id=series_id,
        bookings=bookings,
        conflicts=[],
    )