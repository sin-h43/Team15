from datetime import datetime, timedelta

from flask import Blueprint

from crb.db import get_db

RETENTION_YEARS = 2

bp = Blueprint("retention", __name__, cli_group=None)


def purge_old_audit_records(db, now=None):
    """Delete audit log rows older than RETENTION_YEARS (CRB-NF-004).

    Nothing younger than 2 years is ever deleted. Bookings are never deleted.
    Returns the number of rows removed.
    """
    now = now or datetime.now()
    cutoff = (now - timedelta(days=365 * RETENTION_YEARS)).strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.execute("DELETE FROM audit_log WHERE created_at < ?", (cutoff,))
    db.commit()
    return cursor.rowcount


@bp.cli.command("purge-old-logs")
def purge_old_logs_command():
    """Remove audit log rows older than 2 years. Run it now and then (for example monthly)."""
    count = purge_old_audit_records(get_db())
    print(str(count) + " old audit row(s) removed.")
