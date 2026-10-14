from flask import current_app
from werkzeug.security import generate_password_hash

from crb.db import get_db

USERS = [
    ("employee1", "emp123", "employee"),
    ("admin1", "admin123", "admin"),
    ("auditor1", "aud123", "auditor"),
]

ROOMS = [
    ("Alpha", "Bengaluru", 4, "whiteboard"),
    ("Beta", "Bengaluru", 8, "projector,whiteboard"),
    ("Gamma", "Bengaluru", 12, "projector,video_conf,whiteboard"),
    ("Delta", "Pune", 6, "projector"),
    ("Epsilon", "Pune", 10, "video_conf,whiteboard"),
]


def seed():
    """Add the demo users and rooms (run once, right after init_db).

    Passwords are hashed with a slow, strong method by default. The tests switch
    to a fast method (PASSWORD_HASH_METHOD) so the test suite does not crawl.
    """
    db = get_db()
    method = current_app.config.get("PASSWORD_HASH_METHOD", "pbkdf2:sha256")
    for username, password, role in USERS:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password, method=method), role),
        )
    for name, location, capacity, equipment in ROOMS:
        db.execute(
            "INSERT INTO rooms (name, location, capacity, equipment) VALUES (?, ?, ?, ?)",
            (name, location, capacity, equipment),
        )
    db.commit()