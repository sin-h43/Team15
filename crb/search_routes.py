"""Room search page and JSON endpoint for CRB-F-010."""

from flask import Blueprint, jsonify, render_template, request

from crb.equipment import filter_by_equipment
from crb.guards import login_required
from crb.rooms_repo import search_available_rooms
from crb.validators import (
    ValidationError,
    parse_equipment,
    parse_int,
    parse_range,
    parse_text,
)

search_bp = Blueprint("search", __name__)


def perform_search():
    """Validate search inputs and return matching available rooms."""
    start_time, end_time = parse_range(
        request.args.get("date", ""),
        request.args.get("start", ""),
        request.args.get("end", ""),
    )

    location = (request.args.get("location") or "").strip()
    if len(location) > 100:
        raise ValidationError("Location is too long")

    capacity_text = (request.args.get("capacity") or "").strip()
    capacity = (
        parse_int(capacity_text, "Capacity")
        if capacity_text
        else None
    )

    equipment = parse_equipment(request.args.getlist("equipment"))

    rooms = search_available_rooms(start_time, end_time)

    rooms = [
        room for room in rooms
        if (not location or location.casefold() in room["location"].casefold())
        and (capacity is None or room["capacity"] >= capacity)
    ]

    return filter_by_equipment(rooms, equipment)


@search_bp.route("/rooms/search")
@login_required
def search_page():
    try:
        rooms = perform_search() if request.args else []
    except ValidationError as error:
        return str(error), 400

    return render_template("search.html", rooms=rooms)


@search_bp.route("/api/rooms/search")
@login_required
def search_json():
    try:
        rooms = perform_search()
    except ValidationError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"rooms": rooms})