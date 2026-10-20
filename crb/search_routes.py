from flask import Blueprint, jsonify, render_template, request

from crb.db import get_db
from crb.equipment import split_equipment
from crb.guards import login_required
from crb.search import find_rooms, list_locations
from crb.validators import (
    ALLOWED_EQUIPMENT,
    ValidationError,
    parse_equipment,
    parse_int,
    parse_range,
)

bp = Blueprint("search", __name__)


@bp.route("/rooms/search")
@login_required
def search_rooms():
    db = get_db()
    searched = bool(request.args)
    rooms = []
    error = None

    if searched:
        try:
            start, end = parse_range(
                request.args.get("date"), request.args.get("start"), request.args.get("end")
            )
            capacity = parse_int(request.args.get("capacity") or "1", "Capacity")
            equipment = parse_equipment(request.args.getlist("equipment"))
            rooms = find_rooms(db, start, end, request.args.get("location", ""), capacity, equipment)
        except ValidationError as problem:
            error = str(problem)

    if request.args.get("format") == "json":
        if error:
            return jsonify({"error": error}), 400
        return jsonify(
            [
                {
                    "roomId": room["id"],
                    "name": room["name"],
                    "location": room["location"],
                    "capacity": room["capacity"],
                    "equipment": split_equipment(room["equipment"]),
                }
                for room in rooms
            ]
        )

    return (
        render_template(
            "search.html",
            rooms=rooms,
            error=error,
            searched=searched,
            args=request.args,
            locations=list_locations(db),
            all_equipment=ALLOWED_EQUIPMENT,
        ),
        400 if error else 200,
    )
