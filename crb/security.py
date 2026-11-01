import os


def apply_security_settings(app):
    """Safer cookies and response headers (CRB-SR-001, CRB-SR-004).

    Set the environment variable CRB_HTTPS=1 when the site is served over HTTPS
    (see docs/DEPLOYMENT.md). Then the session cookie is only sent over HTTPS.
    """
    https = os.environ.get("CRB_HTTPS") == "1"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = https

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
