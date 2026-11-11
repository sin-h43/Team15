import hmac
import os
import secrets

from flask import abort, request, session


def apply_security_settings(app):
    """Safer cookies and response headers (CRB-SR-001, CRB-SR-004).

    Set the environment variable CRB_HTTPS=1 when the site is served over HTTPS
    (see docs/DEPLOYMENT.md). Then the session cookie is only sent over HTTPS.
    """
    https = os.environ.get("CRB_HTTPS") == "1"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = https

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        """Reject POSTs that do not carry the session's token (switched off in unit tests)."""
        if not app.config.get("CSRF_ENABLED", not app.config.get("TESTING")):
            return
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token", "")
            expected = session.get("csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
