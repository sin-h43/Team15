# Deployment notes (CRB-SR-001, CRB-NF-004)

## HTTPS (TLS 1.2 or newer) - CRB-SR-001

The Flask development server speaks plain HTTP. Real use needs HTTPS. Two options:

1. **Quick demo with a throw-away certificate** (needs the `cryptography` package, already in `requirements.txt`):

   ```bash
   export CRB_HTTPS=1                      # Windows (cmd): set CRB_HTTPS=1
   flask --app crb.app run --cert=adhoc    # open https://127.0.0.1:5000
   ```

   The browser warns about the certificate because it is self-signed. That is expected for a demo.

2. **Real server:** run the app behind a web server such as nginx or Caddy that holds a real
   certificate and allows only TLS 1.2 and TLS 1.3. Set `CRB_HTTPS=1` for the app so the session
   cookie is marked `Secure` and the `Strict-Transport-Security` header is sent.

## Secrets

Set a long random `CRB_SECRET_KEY` before starting the app. It signs login cookies and is also the
key that encrypts attendee names and emails. If it is lost or changed, the encrypted attendee data
cannot be read any more.

## Log retention - CRB-NF-004

Audit log rows are kept for at least 2 years. To remove rows older than that:

```bash
flask --app crb.app purge-old-logs
```

Bookings are never deleted.

## Reminders

Reminder emails are sent by a job. Run it every minute (cron on Linux/Mac, Task Scheduler on Windows):

```bash
flask --app crb.app send-reminders
```
