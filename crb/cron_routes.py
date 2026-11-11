"""Endpoint for a scheduler (for example Vercel Cron) to run the periodic jobs.

It is switched off unless CRON_SECRET is set, and the caller must send it as
`Authorization: Bearer <secret>` (Vercel Cron does this automatically).
"""
import hmac

from flask import Blueprint, abort, current_app, jsonify, request

from crb.db import get_db
from crb.hold_cleanup import release_expired_holds
from crb.reminders import send_due_reminders

bp = Blueprint("cron", __name__)


@bp.route("/cron/send-reminders")
def run_jobs():
    secret = current_app.config.get("CRON_SECRET")
    if not secret:
        abort(404)
    sent = request.headers.get("Authorization", "")
    if not hmac.compare_digest(sent, "Bearer " + secret):
        abort(401)
    db = get_db()
    return jsonify({
        "reminders_sent": send_due_reminders(db),
        "holds_released": release_expired_holds(db),
    })
