from functools import wraps

from flask import abort, redirect, session


def login_required(view):
    """Send anonymous visitors to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Allow only the listed roles; everybody else gets 403 Forbidden."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect("/login")
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator