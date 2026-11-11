"""One-time email links for verifying an address or resetting a password.

The link carries a random token; only its SHA-256 hash is stored, so a copy of the
database cannot be used to take over an account.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

STAMP = "%Y-%m-%d %H:%M:%S"
LIFETIME_HOURS = {"verify": 48, "reset": 1}


def _hash(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(db, user_id, kind, now=None):
    """Create a new token for the user (older ones of that kind stop working). Returns the raw token."""
    now = now or datetime.now()
    raw = secrets.token_urlsafe(32)
    expires = (now + timedelta(hours=LIFETIME_HOURS[kind])).strftime(STAMP)
    db.execute("DELETE FROM auth_tokens WHERE user_id = ? AND kind = ?", (user_id, kind))
    db.execute(
        "INSERT INTO auth_tokens (user_id, kind, token_hash, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, kind, _hash(raw), expires),
    )
    db.commit()
    return raw


def find_token_user(db, raw, kind, now=None):
    """The user id a still-valid token belongs to, or None. Does not use the token up."""
    now = now or datetime.now()
    row = db.execute(
        "SELECT user_id FROM auth_tokens WHERE token_hash = ? AND kind = ? AND expires_at > ?",
        (_hash(raw or ""), kind, now.strftime(STAMP)),
    ).fetchone()
    return row["user_id"] if row else None


def use_token(db, raw, kind, now=None):
    """Return the user id and make the token unusable; None if it is unknown or expired."""
    user_id = find_token_user(db, raw, kind, now)
    if user_id is None:
        return None
    db.execute("DELETE FROM auth_tokens WHERE token_hash = ?", (_hash(raw),))
    db.commit()
    return user_id
