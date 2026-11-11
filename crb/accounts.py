"""Self-signup, email verification and password reset (CRB-F-001).

Every email goes through notifications.send_email, so for now it lands in the outbox table
(and the link is printed to the server console for local use). A real mail service replaces
that one function later.
"""
import click
from flask import Blueprint, current_app, render_template, request, url_for
from werkzeug.security import generate_password_hash

from crb.db import get_db
from crb.lockout import reset_failures
from crb.notifications import send_email
from crb.tokens import find_token_user, issue_token, use_token
from crb.validators import ValidationError, parse_email, parse_password, parse_username

bp = Blueprint("accounts", __name__, cli_group=None)

GENERIC_MAIL_NOTICE = "If that address can be used, an email with a link is on its way."


def password_hash(password):
    method = current_app.config.get("PASSWORD_HASH_METHOD")
    return generate_password_hash(password, method=method) if method else generate_password_hash(password)


def mail_link(db, user, kind, route, subject, intro):
    """Email the user a one-time link and print it for local use."""
    token = issue_token(db, user["id"], kind)
    link = url_for(route, token=token, _external=True)
    send_email(db, user["username"], subject, intro + "\n\n" + link + "\n\nIf this was not you, ignore this email.")
    current_app.logger.info("%s link for %s: %s", kind, user["username"], link)
    if not current_app.config.get("TESTING"):
        print(kind + " link for " + user["username"] + ": " + link, flush=True)
    return link


def find_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def message(title, text, status=200, back_url="/login", back_text="Back to log in"):
    page = render_template("message.html", title=title, message=text, back_url=back_url, back_text=back_text)
    return page, status


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    values = {"username": request.form.get("username", ""), "email": request.form.get("email", "")}
    if request.method == "GET":
        return render_template("signup.html", error=None, values={})
    db = get_db()
    try:
        username = parse_username(request.form.get("username"))
        email = parse_email(request.form.get("email"))
        password = parse_password(request.form.get("password"))
        if password != request.form.get("confirm", ""):
            raise ValidationError("The two passwords do not match")
        taken = db.execute("SELECT 1 FROM users WHERE LOWER(username) = ?", (username.lower(),)).fetchone()
        if taken:
            raise ValidationError("That username is already taken")
    except ValidationError as problem:
        return render_template("signup.html", error=str(problem), values=values), 400

    if find_by_email(db, email) is None:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, role, email, email_verified) "
            "VALUES (?, ?, 'employee', ?, 0)",
            (username, password_hash(password), email),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        mail_link(db, user, "verify", "accounts.verify", "Confirm your email address",
                  "Welcome to Conference Room Booking. Confirm your email address to activate your account:")
    # The same answer whether or not the address was already registered (no account probing).
    return message("Check your email", "We sent a confirmation link to " + email
                   + ". Open it to activate your account.")


@bp.route("/verify/<token>")
def verify(token):
    db = get_db()
    user_id = use_token(db, token, "verify")
    if user_id is None:
        return message("Link not valid", "This confirmation link is invalid or has expired. "
                       "You can request a new one.", 400, "/resend-verification", "Send a new link")
    db.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    db.commit()
    return message("Email confirmed", "Your account is active. You can log in now.")


@bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "GET":
        return render_template("email_form.html", title="Send a new confirmation link", error=None, button="Send link")
    db = get_db()
    try:
        email = parse_email(request.form.get("email"))
    except ValidationError as problem:
        return render_template("email_form.html", title="Send a new confirmation link",
                               error=str(problem), button="Send link"), 400
    user = find_by_email(db, email)
    if user is not None and not user["email_verified"]:
        mail_link(db, user, "verify", "accounts.verify", "Confirm your email address",
                  "Confirm your email address to activate your account:")
    return message("Check your email", GENERIC_MAIL_NOTICE)


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return render_template("email_form.html", title="Reset your password", error=None, button="Send reset link")
    db = get_db()
    try:
        email = parse_email(request.form.get("email"))
    except ValidationError as problem:
        return render_template("email_form.html", title="Reset your password",
                               error=str(problem), button="Send reset link"), 400
    user = find_by_email(db, email)
    if user is not None:
        mail_link(db, user, "reset", "accounts.reset", "Reset your password",
                  "Use this link within 1 hour to choose a new password:")
    return message("Check your email", GENERIC_MAIL_NOTICE)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    db = get_db()
    if find_token_user(db, token, "reset") is None:
        return message("Link not valid", "This reset link is invalid or has expired.",
                       400, "/forgot", "Request a new link")
    if request.method == "GET":
        return render_template("reset.html", error=None)
    try:
        password = parse_password(request.form.get("password"))
        if password != request.form.get("confirm", ""):
            raise ValidationError("The two passwords do not match")
    except ValidationError as problem:
        return render_template("reset.html", error=str(problem)), 400
    user_id = use_token(db, token, "reset")
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    # Having received the email proves the address, so the account is also confirmed.
    db.execute("UPDATE users SET password_hash = ?, email_verified = 1 WHERE id = ?",
               (password_hash(password), user_id))
    db.commit()
    reset_failures(db, user)
    return message("Password changed", "Your password has been updated. You can log in now.")


@bp.cli.command("create-user")
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--role", type=click.Choice(["employee", "admin", "auditor"]), default="employee", show_default=True)
@click.password_option()
def create_user_command(username, email, role, password):
    """Create an already-confirmed account (use it to create the first admin)."""
    db = get_db()
    try:
        username, email, password = parse_username(username), parse_email(email), parse_password(password)
    except ValidationError as problem:
        raise click.ClickException(str(problem))
    if db.execute("SELECT 1 FROM users WHERE LOWER(username) = ? OR email = ?",
                  (username.lower(), email)).fetchone():
        raise click.ClickException("That username or email is already in use")
    db.execute(
        "INSERT INTO users (username, password_hash, role, email, email_verified) VALUES (?, ?, ?, ?, 1)",
        (username, password_hash(password), role, email),
    )
    db.commit()
    print("Created " + role + " account " + username + ".")
