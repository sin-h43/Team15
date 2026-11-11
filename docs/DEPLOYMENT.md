# Deploying to Vercel with a Neon database

This is a checklist. Steps marked **you** need your own accounts or secrets; do them in the browser or in the
Vercel dashboard and never paste keys into chat, code or git. The app itself is ready: `app.py` (the entry point
Vercel looks for), `public/static/` (served by Vercel's CDN), `requirements.txt` (runtime only) and `.vercelignore`.

1. **(you) Create a Neon project** at neon.tech and copy the *pooled* connection string
   (`postgresql://...?sslmode=require`). Or add Neon from Vercel's Marketplace, which sets `DATABASE_URL` for you.
2. **Create the tables** from your own computer, once (this erases that database, so use a new, empty one):
   ```bash
   export DATABASE_URL="postgresql://...neon connection string..."
   flask --app crb.app init-db --empty --yes
   flask --app crb.app create-user --role admin      # asks for username, email and password
   ```
   On Windows PowerShell use `$env:DATABASE_URL = "..."`.
3. **(you) Push the repository to GitHub** and import it as a new project in Vercel. Vercel detects Flask from
   `app.py`. No build command is needed.
4. **(you) Set environment variables** in Vercel (Project Settings, Environment Variables, Production):

   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | the Neon connection string |
   | `CRB_SECRET_KEY` | a long random string, e.g. `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `CRB_HTTPS` | `1` (secure cookies and HSTS) |
   | `CRB_TRUST_PROXY` | `1` (use the real client address for rate limits) |
   | `RESEND_API_KEY` | key from resend.com |
   | `CRB_MAIL_FROM` | `Conference Rooms <rooms@your-verified-domain>` |
   | `CRON_SECRET` | a long random string |
   | `CRB_TIMEZONE` | your local timezone, e.g. `Asia/Kolkata`. Vercel runs on UTC; without this, "in the past" checks and reminders are off by hours |

   The app refuses to start on Vercel without `DATABASE_URL`, and over HTTPS without a real `CRB_SECRET_KEY`.
   Changing `CRB_SECRET_KEY` later makes stored attendee names and emails unreadable.
5. **(you) Resend:** verify a sending domain, otherwise Resend only delivers to your own account address.
6. **Redeploy** after setting variables, open the site, log in as the admin you created, add rooms, and sign up a
   second account to check the confirmation email arrives.
7. **Reminders:** Vercel's free (Hobby) plan can only run cron jobs once a day, with up to an hour of drift, which
   is too coarse for 10-minute reminders. Options:
   - **Pro plan:** add a `vercel.json` with
     `{"crons": [{"path": "/cron/send-reminders", "schedule": "* * * * *"}]}`. Vercel sends
     `Authorization: Bearer <CRON_SECRET>` automatically.
   - **Free:** use an external scheduler such as cron-job.org to call
     `https://<your-site>/cron/send-reminders` every minute with the header `Authorization: Bearer <CRON_SECRET>`.

Verified locally: the whole test suite on SQLite and PostgreSQL, the entry point importing, and static files served
from `public/static`. **Not verified:** the deployment itself, because it needs your Vercel, Neon and Resend accounts.
If Vercel does not detect the app, set `[tool.vercel] entrypoint = "app:app"` in a `pyproject.toml`.

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

## Real email (Resend)

Set these environment variables to send real email (CRB-F-060/061/062, sign-up and reset links):

| Variable | Meaning |
|----------|---------|
| `RESEND_API_KEY` | API key from resend.com. Without it nothing is sent; emails are only saved in the outbox. |
| `CRB_MAIL_FROM` | Sender, e.g. `Conference Rooms <rooms@yourdomain.com>`. Defaults to Resend's test sender `onboarding@resend.dev`, which only delivers to your own Resend account address. To email anyone, verify a domain in Resend and use an address on it. |

Every email is still saved in the outbox, with a status: `sent`, `failed` (the service refused it; the
booking is not affected) or `stored` (no key, or a demo `.example` address). Never put the key in the code
or in git; keep it in the environment.

Abuse limits: at most 3 sign-up/reset emails an hour per address and 10 requests an hour per network address.
Behind a proxy such as Vercel set `CRB_TRUST_PROXY=1` so the real client address is used.

## Reminders (scheduler endpoint)

Hosts without a long-running process cannot run `send-reminders` themselves. Set `CRON_SECRET` and have a
scheduler (for example Vercel Cron, or any pinger) call `GET /cron/send-reminders` with the header
`Authorization: Bearer <CRON_SECRET>` every minute. It sends the due reminders and releases expired holds.
Without `CRON_SECRET` the endpoint does not exist (404).

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
