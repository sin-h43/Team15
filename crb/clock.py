"""The app's idea of "now": local time in the configured timezone.

People type local times (a booking at 10:00 means 10:00 where they are), but a cloud server
runs on UTC. Set CRB_TIMEZONE (for example Asia/Kolkata) so "in the past", hold timers and
reminders use local time. Without it the machine's own local time is used.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_now():
    """A naive datetime holding the current local time."""
    name = os.environ.get("CRB_TIMEZONE")
    if not name:
        return datetime.now()
    try:
        return datetime.now(ZoneInfo(name)).replace(tzinfo=None)
    except ZoneInfoNotFoundError:
        raise RuntimeError("CRB_TIMEZONE is not a valid timezone name: " + name)
