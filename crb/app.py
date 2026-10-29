import os

from flask import Flask, render_template
from crb.admin_routes import admin_bp

from crb.db import close_db, init_db
from crb.seed import seed


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("CRB_SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE"] = os.path.join(os.path.dirname(app.root_path), "crb.db")
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.cli.command("init-db")
    def init_db_command():
        """Create empty tables and load demo users and rooms (wipes old data)."""
        init_db()
        seed()
        print("Database ready with demo data.")

    # Each module owner adds their blueprint under their own marker below.

    # SLOT-AUTH
    from crb.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

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
    # SLOT-NOTIFY
    from crb.reminders import bp as reminders_bp
    app.register_blueprint(reminders_bp)
    from crb.notify_routes import bp as notify_bp
    app.register_blueprint(notify_bp)
    # SLOT-REPORT
    from crb.report_routes import bp as report_bp
    app.register_blueprint(report_bp)
    # SLOT-SECURITY

    return app