import pytest

from crb.validators import (
    ValidationError,
    parse_equipment,
    parse_int,
    parse_range,
    parse_text,
)


def test_parse_int_accepts_a_number_string():
    assert parse_int("8", "Capacity") == 8


def test_parse_int_rejects_text():
    with pytest.raises(ValidationError):
        parse_int("abc", "Capacity")


def test_parse_int_rejects_missing_value():
    with pytest.raises(ValidationError):
        parse_int(None, "Capacity")


def test_parse_int_rejects_zero():
    with pytest.raises(ValidationError):
        parse_int("0", "Capacity")


def test_parse_text_strips_spaces():
    assert parse_text("  Alpha  ", "Name") == "Alpha"


def test_parse_text_rejects_empty():
    with pytest.raises(ValidationError):
        parse_text("   ", "Name")


def test_parse_text_rejects_too_long():
    with pytest.raises(ValidationError):
        parse_text("x" * 101, "Name")


def test_parse_range_returns_formatted_strings():
    assert parse_range("2030-01-15", "10:00", "11:30") == ("2030-01-15 10:00", "2030-01-15 11:30")


def test_parse_range_rejects_end_before_start():
    with pytest.raises(ValidationError, match="Invalid time range"):
        parse_range("2030-01-15", "11:00", "10:00")


def test_parse_range_rejects_equal_times():
    with pytest.raises(ValidationError, match="Invalid time range"):
        parse_range("2030-01-15", "10:00", "10:00")


def test_parse_range_rejects_impossible_date():
    with pytest.raises(ValidationError):
        parse_range("2030-02-31", "10:00", "11:00")


def test_parse_range_rejects_missing_values():
    with pytest.raises(ValidationError):
        parse_range(None, None, None)


def test_parse_equipment_accepts_known_items():
    assert parse_equipment(["projector", "whiteboard"]) == ["projector", "whiteboard"]


def test_parse_equipment_rejects_unknown_item():
    with pytest.raises(ValidationError):
        parse_equipment(["laser"])