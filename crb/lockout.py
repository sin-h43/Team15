from datetime import datetime, timedelta

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def is_locked(user, now):
    """True while the account is still inside its lock window."""
    if user["locked_until"] is None:
        return False
    return now < datetime.strptime(user["locked_until"], TIME_FORMAT)


def record_failure(db, user, now):
    """Count one wrong password; lock the account when the limit is reached."""
    attempts = user["failed_attempts"] + 1
    locked_until = None
    if attempts >= MAX_ATTEMPTS:
        locked_until = (now + timedelta(minutes=LOCK_MINUTES)).strftime(TIME_FORMAT)
        attempts = 0
    db.execute(
        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
        (attempts, locked_until, user["id"]),
    )
    db.commit()


def reset_failures(db, user):
    db.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (user["id"],),
    )
    db.commit()