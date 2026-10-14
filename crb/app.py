import os

from flask import Flask, render_template

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

    # SLOT-AUDIT

    # SLOT-SEARCH

    # SLOT-ADMIN

    return app