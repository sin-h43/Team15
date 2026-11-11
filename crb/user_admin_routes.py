"""Admin page for choosing who is an employee, admin or auditor (CRB-F-002, CRB-SR-003)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, session

from crb.audit import log_action
from crb.db import get_db
from crb.guards import role_required

bp = Blueprint("user_admin", __name__, url_prefix="/admin")

ROLES = ("employee", "admin", "auditor")


@bp.route("/users")
@role_required("admin")
def users():
    rows = get_db().execute(
        "SELECT id, username, email, role, email_verified FROM users ORDER BY username"
    ).fetchall()
    return render_template("admin_users.html", users=rows, roles=ROLES)


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def change_role(user_id):
    db = get_db()
    role = request.form.get("role", "")
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if role not in ROLES:
        flash("Unknown role.", "error")
    elif user_id == session["user_id"]:
        flash("You cannot change your own role.", "error")
    elif user["role"] != role:
        db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        db.commit()
        log_action(db, session["username"], "USER_ROLE_CHANGED",
                   user["username"] + ": " + user["role"] + " -> " + role)
        flash(user["username"] + " is now " + role + ".", "success")
    return redirect("/admin/users")
