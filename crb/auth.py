from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash

from crb.db import get_db
from crb.lockout import LOCK_MINUTES, is_locked, record_failure, reset_failures

bp = Blueprint("auth", __name__)

SESSION_MINUTES = 30


@bp.record_once
def set_session_timeout(state):
    """Sessions expire after 30 idle minutes (CRB-SR-004)."""
    state.app.permanent_session_lifetime = timedelta(minutes=SESSION_MINUTES)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    now = datetime.now()

    if user is not None and is_locked(user, now):
        message = "Account locked for " + str(LOCK_MINUTES) + " minutes. Try again later."
        return render_template("login.html", error=message), 403

    if user is None or not check_password_hash(user["password_hash"], password):
        if user is not None:
            record_failure(db, user, now)
        return render_template("login.html", error="Invalid username or password."), 401

    reset_failures(db, user)
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return redirect("/")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")
