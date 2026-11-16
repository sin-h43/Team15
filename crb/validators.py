import re
from datetime import datetime

TIME_FORMAT = "%Y-%m-%d %H:%M"
ALLOWED_EQUIPMENT = ["projector", "video_conf", "whiteboard"]


class ValidationError(ValueError):
    """Raised when a value typed by a user is not acceptable."""


def parse_int(value, name, minimum=1):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(name + " must be a whole number")
    if number < minimum:
        raise ValidationError(name + " must be at least " + str(minimum))
    return number


def parse_text(value, name, max_length=100):
    text = (value or "").strip()
    if not text:
        raise ValidationError(name + " is required")
    if len(text) > max_length:
        raise ValidationError(name + " is too long")
    return text


def parse_range(date_text, start_text, end_text):
    """Turn a date and two times into two 'YYYY-MM-DD HH:MM' strings."""
    try:
        start = datetime.strptime(date_text + " " + start_text, TIME_FORMAT)
        end = datetime.strptime(date_text + " " + end_text, TIME_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError("Invalid date or time")
    if end <= start:
        raise ValidationError("Invalid time range")
    return start.strftime(TIME_FORMAT), end.strftime(TIME_FORMAT)


def parse_equipment(values):
    for item in values:
        if item not in ALLOWED_EQUIPMENT:
            raise ValidationError("Unknown equipment: " + item)
    return list(values)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def parse_username(value):
    text = (value or "").strip()
    if not USERNAME_PATTERN.match(text):
        raise ValidationError("Username must be 3-30 letters, digits, dots, dashes or underscores")
    return text


def parse_email(value):
    text = (value or "").strip().lower()
    if len(text) > 254 or not EMAIL_PATTERN.match(text):
        raise ValidationError("Enter a valid email address")
    return text


def parse_password(value):
    text = value or ""
    if len(text) < MIN_PASSWORD_LENGTH:
        raise ValidationError("Password must be at least " + str(MIN_PASSWORD_LENGTH) + " characters")
    if len(text) > 200:
        raise ValidationError("Password is too long")
    return text
