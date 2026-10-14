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