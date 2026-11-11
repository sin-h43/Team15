"""Sending real email through Resend (CRB-F-060/061/062).

Mail is only sent when RESEND_API_KEY is set. Without it the app still works: every email is
saved in the outbox table and nothing leaves the machine. The key is read from the environment
and is never logged or stored.
"""
import json
import urllib.error
import urllib.request

from flask import current_app

API_URL = "https://api.resend.com/emails"
DEFAULT_SENDER = "Conference Room Booking <onboarding@resend.dev>"


class MailError(Exception):
    """The mail service refused or could not be reached."""


def mail_enabled():
    return bool(current_app.config.get("RESEND_API_KEY"))


def can_deliver_to(address):
    """False for addresses that can never receive mail (the reserved .example demo domain)."""
    return bool(address) and not address.lower().endswith(".example")


def deliver(to_address, subject, body):
    """Send one plain-text email. Raises MailError on any failure."""
    payload = json.dumps({
        "from": current_app.config.get("MAIL_FROM") or DEFAULT_SENDER,
        "to": [to_address],
        "subject": subject,
        "text": body,
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + current_app.config["RESEND_API_KEY"],
            "Content-Type": "application/json",
            "User-Agent": "crb-app/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status >= 300:
                raise MailError("mail service answered " + str(response.status))
    except urllib.error.HTTPError as problem:
        raise MailError("mail service answered " + str(problem.code))
    except (urllib.error.URLError, TimeoutError, OSError) as problem:
        raise MailError("could not reach the mail service: " + str(problem))
