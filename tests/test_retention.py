from datetime import datetime

from crb.db import get_db
from crb.retention import RETENTION_YEARS, purge_old_audit_records

NOW = datetime(2030, 6, 1, 12, 0, 0)


def add_audit(app, when):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO audit_log (actor, action, detail, created_at) VALUES ('admin1', 'X', 'd', ?)", (when,)
        )
        db.commit()


def audit_times(app):
    with app.app_context():
        rows = get_db().execute("SELECT created_at FROM audit_log ORDER BY id").fetchall()
    return [row["created_at"] for row in rows]


def test_retention_is_two_years():
    assert RETENTION_YEARS == 2


def test_old_rows_are_removed_and_recent_rows_stay(app):
    add_audit(app, "2027-01-01 10:00:00")  # more than 2 years old
    add_audit(app, "2028-07-01 10:00:00")  # about 2 years old: kept
    add_audit(app, "2030-05-30 10:00:00")
    with app.app_context():
        assert purge_old_audit_records(get_db(), NOW) == 1
    assert audit_times(app) == ["2028-07-01 10:00:00", "2030-05-30 10:00:00"]


def test_nothing_to_remove_returns_zero(app):
    add_audit(app, "2030-05-30 10:00:00")
    with app.app_context():
        assert purge_old_audit_records(get_db(), NOW) == 0


def test_bookings_are_never_purged(app):
    from tests.helpers import make_booking

    make_booking(app, start="2020-01-15 10:00", end="2020-01-15 11:00")
    with app.app_context():
        purge_old_audit_records(get_db(), NOW)
        assert get_db().execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1


def test_command_line_job_reports_the_count(app):
    add_audit(app, "2001-01-01 10:00:00")
    result = app.test_cli_runner().invoke(args=["purge-old-logs"])
    assert "1 old audit row(s) removed." in result.output
