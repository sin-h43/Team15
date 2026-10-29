from flask import Blueprint, render_template

from crb.attendees import email_for
from crb.db import get_db
from crb.guards import role_required

bp = Blueprint("notify", __name__)


@bp.route("/outbox")
@role_required("admin")
def outbox():
    """Show the latest emails the system has sent (admin only)."""
    rows = get_db().execute("SELECT * FROM outbox ORDER BY id DESC LIMIT 100").fetchall()
    mails = [{"row": row, "address": email_for(row["to_username"])} for row in rows]
    return render_template("outbox.html", mails=mails)