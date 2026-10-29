import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app


def make_cipher():
    """Build the cipher from the app's PII_KEY (or, if that is not set, from SECRET_KEY).

    Set CRB_SECRET_KEY to a long random value in real use. If the key is lost or changed,
    the encrypted attendee data can no longer be read.
    """
    secret = current_app.config.get("PII_KEY") or current_app.config["SECRET_KEY"]
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_text(plain):
    """Turn readable text into an unreadable token that can be stored in the database."""
    return make_cipher().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_text(token):
    """Turn a stored token back into readable text."""
    return make_cipher().decrypt(token.encode("ascii")).decode("utf-8")
