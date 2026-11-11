import os

import click

from flask import Flask, render_template
from crb.admin_routes import admin_bp

from crb.db import close_db, database_url_from_env, init_db, is_postgres
from crb.seed import seed


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("CRB_SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE"] = os.path.join(os.path.dirname(app.root_path), "crb.db")
    testing = bool(test_config and test_config.get("TESTING"))
    app.config["DATABASE_URL"] = database_url_from_env(testing)
    # Real email and the cron endpoint are configured from the environment (never in tests).
    if not testing:
        app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY") or None
        app.config["MAIL_FROM"] = os.environ.get("CRB_MAIL_FROM") or None
        app.config["CRON_SECRET"] = os.environ.get("CRON_SECRET") or None
        if os.environ.get("CRB_TRUST_PROXY") == "1":  # behind a proxy such as Vercel
            from werkzeug.middleware.proxy_fix import ProxyFix

            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.cli.command("init-db")
    @click.option("--yes", is_flag=True, help="Do not ask before wiping a Postgres database.")
    @click.option("--empty", is_flag=True, help="Create the tables only, without demo users and rooms.")
    def init_db_command(yes, empty):
        """Create empty tables and load demo users and rooms (wipes old data)."""
        if is_postgres() and not yes:
            click.confirm("This ERASES all CRB tables in the DATABASE_URL database. Continue?", abort=True)
        init_db()
        if empty:
            print("Database ready (empty).")
            return
        seed()
        print("Database ready with demo data.")

    # Each module owner adds their blueprint under their own marker below.

    # SLOT-AUTH
    from crb.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from crb.user_admin_routes import bp as user_admin_bp
    app.register_blueprint(user_admin_bp)
    from crb.accounts import bp as accounts_bp
    app.register_blueprint(accounts_bp)

    # SLOT-AUDIT
    from crb.audit import bp as audit_bp
    app.register_blueprint(audit_bp)

    # SLOT-SEARCH
    from crb.search_routes import bp as search_bp
    app.register_blueprint(search_bp)

    # SLOT-ADMIN
    app.register_blueprint(admin_bp)

    # Sprint 2 extension points: each owner adds two lines under their own marker.
     # SLOT-BOOKING
    from crb.booking_routes import bp as booking_bp
    app.register_blueprint(booking_bp)

    from crb.reschedule_routes import bp as reschedule_bp
    app.register_blueprint(reschedule_bp)

    # SLOT-VIEW
    from crb.bookings_view import bp as view_bp
    app.register_blueprint(view_bp)

    # SLOT-ATTENDEES
    from crb.attendee_routes import bp as attendee_bp
    app.register_blueprint(attendee_bp)

    # SLOT-CANCEL
    from crb.cancel_routes import bp as cancel_bp
    app.register_blueprint(cancel_bp)

    # SLOT-RECURRING
    from crb.recurring_routes import bp as recurring_bp
    app.register_blueprint(recurring_bp)
    # SLOT-NOTIFY
    from crb.reminders import bp as reminders_bp
    app.register_blueprint(reminders_bp)
    from crb.notify_routes import bp as notify_bp
    app.register_blueprint(notify_bp)
    from crb.cron_routes import bp as cron_bp
    app.register_blueprint(cron_bp)
    # SLOT-REPORT
    from crb.report_routes import bp as report_bp
    app.register_blueprint(report_bp)
    # SLOT-SECURITY
    from crb.security import apply_security_settings
    apply_security_settings(app)
    from crb.retention import bp as retention_bp
    app.register_blueprint(retention_bp)


    return app