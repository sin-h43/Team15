from datetime import datetime

from flask import Blueprint, render_template

from crb.db import get_db
from crb.guards import role_required

bp = Blueprint("audit", __name__)


def log_action(db, actor, action, detail):
    """Record who did what (CRB-SR-003). Call this after every admin action."""
    db.execute(
        "INSERT INTO audit_log (actor, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (actor, action, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    db.commit()


@bp.route("/audit")
@role_required("admin", "auditor")
def audit_view():
    rows = get_db().execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
    return render_template("audit.html", rows=rows)
