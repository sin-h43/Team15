"""A small database-backed rate limit, so strangers cannot make the app send floods of email."""
from datetime import datetime, timedelta
from crb.clock import local_now

STAMP = "%Y-%m-%d %H:%M:%S"


def allow(db, bucket, limit, window_minutes, now=None):
    """Count one use of `bucket`; False when it has already been used `limit` times in the window."""
    now = now or local_now()
    since = (now - timedelta(minutes=window_minutes)).strftime(STAMP)
    db.execute("DELETE FROM rate_limit WHERE created_at < ?", (since,))
    used = db.execute(
        "SELECT COUNT(*) FROM rate_limit WHERE bucket = ? AND created_at >= ?", (bucket, since)
    ).fetchone()[0]
    if used >= limit:
        db.commit()
        return False
    db.execute("INSERT INTO rate_limit (bucket, created_at) VALUES (?, ?)", (bucket, now.strftime(STAMP)))
    db.commit()
    return True
