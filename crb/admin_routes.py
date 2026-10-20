
"""Admin routes for room and maintenance management."""

from datetime import datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for
)

from crb.blocks_repo import create_block, delete_block, list_blocks
from crb.db import get_db
from crb.guards import role_required
from crb.rooms_repo import (
    create_room,
    deactivate_room,
    get_room,
    list_rooms,
    update_room,
)
from crb.validators import ValidationError, parse_int, parse_text

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def read_room_form():
    """Validate and return room form values."""
    name = parse_text(request.form.get("name"), "Room name")
    location = parse_text(request.form.get("location"), "Location")
    capacity = parse_int(request.form.get("capacity"), "Capacity")
    equipment = (request.form.get("equipment") or "").strip()
    return name, location, capacity, equipment


def write_audit(action, detail):
    """Record an administrative action."""
    db = get_db()
    db.execute(
        """
        INSERT INTO audit_log (actor, action, detail, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            "admin",
            action,
            detail,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    db.commit()


@admin_bp.route("/rooms")
@role_required("admin")
def rooms():
    return render_template(
        "admin_rooms.html",
        rooms=list_rooms(include_inactive=True),
    )


@admin_bp.route("/rooms/new", methods=["GET", "POST"])
@role_required("admin")
def new_room():
    if request.method == "POST":
        try:
            name, location, capacity, equipment = read_room_form()
        except ValidationError as error:
            flash(str(error), "error")
            return render_template("room_form.html", room=None), 400

        room_id = create_room(name, location, capacity, equipment)
        write_audit("room_created", f"Room {room_id} created")
        flash("Room created successfully.", "success")
        return redirect(url_for("admin.rooms"))

    return render_template("room_form.html", room=None)


@admin_bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_room(room_id):
    room = get_room(room_id)
    if room is None:
        abort(404)

    if request.method == "POST":
        try:
            name, location, capacity, equipment = read_room_form()
        except ValidationError as error:
            flash(str(error), "error")
            return render_template("room_form.html", room=room), 400

        update_room(room_id, name, location, capacity, equipment)
        write_audit("room_updated", f"Room {room_id} updated")
        flash("Room updated successfully.", "success")
        return redirect(url_for("admin.rooms"))

    return render_template("room_form.html", room=room)


@admin_bp.route("/rooms/<int:room_id>/deactivate", methods=["POST"])
@role_required("admin")
def deactivate(room_id):
    if get_room(room_id) is None:
        abort(404)

    deactivate_room(room_id)
    write_audit("room_deactivated", f"Room {room_id} deactivated")
    flash("Room deactivated.", "success")
    return redirect(url_for("admin.rooms"))


@admin_bp.route("/blocks")
@role_required("admin")
def blocks():
    return render_template(
        "admin_blocks.html",
        blocks=list_blocks(),
        rooms=list_rooms(),
    )


@admin_bp.route("/blocks/new", methods=["POST"])
@role_required("admin")
def new_block():
    try:
        room_id = parse_int(request.form.get("room_id"), "Room ID")
        start_time = parse_text(request.form.get("start_time"), "Start time")
        end_time = parse_text(request.form.get("end_time"), "End time")
        reason = parse_text(request.form.get("reason"), "Reason")

        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        if end <= start:
            raise ValidationError("End time must be later than start time")
    except (ValidationError, ValueError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.blocks"))

    room = get_room(room_id)
    if room is None:
        abort(404)
    if not room["active"]:
        flash("Cannot block an inactive room.", "error")
        return redirect(url_for("admin.blocks"))

    start_time = start.strftime("%Y-%m-%d %H:%M")
    end_time = end.strftime("%Y-%m-%d %H:%M")
    block_id = create_block(room_id, start_time, end_time, reason)
    write_audit("maintenance_block_created", f"Block {block_id} created")
    flash("Maintenance block created.", "success")
    return redirect(url_for("admin.blocks"))


@admin_bp.route("/blocks/<int:block_id>/delete", methods=["POST"])
@role_required("admin")
def remove_block(block_id):
    if not delete_block(block_id):
        abort(404)

    write_audit("maintenance_block_deleted", f"Block {block_id} deleted")
    flash("Maintenance block deleted.", "success")
    return redirect(url_for("admin.blocks"))
