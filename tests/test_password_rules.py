"""Password rules for sign-up, reset and the create-user command."""
import pytest

from crb.validators import ValidationError, parse_password

GOOD = "Blue#Tiger42"


def test_a_strong_password_is_accepted():
    assert parse_password(GOOD, "priya", "priya@example.com") == GOOD


@pytest.mark.parametrize("password, fragment", [
    ("Ab#1", "at least 8"),
    ("blue#tiger42", "uppercase"),
    ("BLUE#TIGER42", "lowercase"),
    ("Blue#Tigers", "digit"),
    ("BlueTiger42", "symbol"),
    ("Blue#Tiiger42", None),            # two in a row is fine
    ("Blue#Tigerr42", None),
    ("Blueee#Tiger42", "repeat"),       # three in a row
    ("Aaaaaaa#1", "repeat"),
    ("Password1!", "common"),
    ("Admin123!", "common"),
])
def test_each_rule_is_enforced(password, fragment):
    if fragment is None:
        assert parse_password(password) == password
    else:
        with pytest.raises(ValidationError, match=fragment):
            parse_password(password)


def test_password_may_not_contain_the_username_or_email_name():
    with pytest.raises(ValidationError, match="username"):
        parse_password("Priya#Tiger42", "priya", "x@example.com")
    with pytest.raises(ValidationError, match="email"):
        parse_password("Rahul#Tiger42", "someone", "rahul.s@example.com".replace(".s", ""))


def test_too_long_password_is_refused():
    with pytest.raises(ValidationError, match="too long"):
        parse_password("Aa#1" + "xy" * 100)


def test_signup_page_shows_the_rules_and_rejects_a_weak_password(app):
    client = app.test_client()
    page = client.get("/signup").get_data(as_text=True)
    assert "uppercase letter" in page and "common password" in page
    weak = client.post("/signup", data={
        "username": "priya", "email": "priya@example.org", "password": "longenough1", "confirm": "longenough1"})
    assert weak.status_code == 400 and b"uppercase" in weak.data


def test_reset_page_rejects_a_weak_password_and_accepts_a_strong_one(app):
    from crb.db import get_db
    from crb.tokens import issue_token

    with app.app_context():
        link = "/reset/" + issue_token(get_db(), 1, "reset")
    client = app.test_client()
    assert client.post(link, data={"password": "weakweakweak", "confirm": "weakweakweak"}).status_code == 400
    assert client.post(link, data={"password": GOOD, "confirm": GOOD}).status_code == 200
    assert client.post("/login", data={"username": "employee1", "password": GOOD}).status_code == 302


def test_create_user_command_refuses_a_weak_password(app):
    result = app.test_cli_runner().invoke(
        args=["create-user", "--username", "boss", "--email", "boss@example.com", "--role", "admin"],
        input="weakpassword\nweakpassword\n",
    )
    assert result.exit_code != 0 and "uppercase" in result.output
