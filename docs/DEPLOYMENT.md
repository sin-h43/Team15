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


## Accounts

Sign-up, email confirmation and password reset use one-time links (stored only as hashes). Until a mail
service is connected the links are saved in the `outbox` table and printed to the server console.
On a fresh database create the first admin with:

```bash
flask --app crb.app init-db --empty
flask --app crb.app create-user --role admin
```

## Database: SQLite or Postgres (ADR-07)

By default the app uses the SQLite file `crb.db`. For hosting (for example on Vercel, which has no
persistent disk) set `DATABASE_URL` to a Postgres address such as a Neon connection string
(use the pooled one, with `sslmode=require`):

```bash
export DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
flask --app crb.app init-db --empty   # creates the tables only (asks before wiping)
```

All SQL is written once in `crb/db.py`'s dialect-neutral form, so no other code changes between engines.
Double-booking is prevented on both engines by one write lock around check-and-insert
(`BEGIN IMMEDIATE` on SQLite, a Postgres advisory lock on Postgres).

`init-db` erases the tables. On Postgres it asks for confirmation (`--yes` skips the question);
`--empty` skips the demo users, whose passwords are public.

### Running the tests on Postgres

The tests use SQLite by default. To run the same suite on Postgres, point `CRB_TEST_DATABASE_URL`
at a throw-away database (the tests wipe it). `DATABASE_URL` is never used by the tests.

```bash
docker run -d --name crb-pg-test -e POSTGRES_PASSWORD=crbtest -e POSTGRES_DB=crb_test -p 54329:5432 postgres:16-alpine
export CRB_TEST_DATABASE_URL="postgresql://postgres:crbtest@localhost:54329/crb_test"
python -m pytest
```
