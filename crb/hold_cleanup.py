from datetime import datetime


def release_expired_holds(db, now=None):
    """Mark every hold whose 2 minutes have run out as 'expired' (CRB-F-032).

    Returns how many holds were released. Expired holds never block a room anyway
    (see availability.py); this keeps the data tidy.
    """
    now_text = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.execute(
        "UPDATE bookings SET status = 'expired' WHERE status = 'held' AND hold_expires_at <= ?",
        (now_text,),
    )
    db.commit()
    return cursor.rowcount