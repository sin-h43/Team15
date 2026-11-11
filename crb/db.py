"""Database access (ADR-07).

All SQL in the app is written once, with `?` placeholders, and runs on either engine:

  * SQLite  - the default (local development and the test suite).
  * Postgres - when the app config has DATABASE_URL (production, e.g. Neon on Vercel).

This module hides the differences, so no other module needs to know which engine is in use:
placeholders, `lastrowid`, row objects, the write lock and the schema.
"""

import os
import sqlite3

from flask import current_app, g

try:  # psycopg is only needed when DATABASE_URL is set
    import psycopg
except ImportError:  # pragma: no cover - SQLite-only installs
    psycopg = None

IntegrityErrors = (sqlite3.IntegrityError,) + ((psycopg.IntegrityError,) if psycopg else ())

# One number for every booking write, so two requests never check-and-insert at once.
BOOKING_WRITE_LOCK = 727001


class Row(dict):
    """A result row: read it by column name (row["name"]) or position (row[0])."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    return lambda values: Row(zip(names, values))


class Cursor:
    """What `execute` returns on Postgres: the same few attributes sqlite3 gives."""

    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class Connection:
    """A database connection for one request, with the same API on both engines."""

    def __init__(self, raw, postgres):
        self.raw = raw
        self.postgres = postgres

    def execute(self, sql, params=()):
        if not self.postgres:
            return self.raw.execute(sql, params)
        params = tuple(params)
        wants_id = (
            sql.lstrip().upper().startswith("INSERT") and "RETURNING" not in sql.upper()
        )
        if wants_id:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        if params:
            sql = sql.replace("%", "%%").replace("?", "%s")
            cursor = self.raw.execute(sql, params)
        else:
            cursor = self.raw.execute(sql)
        lastrowid = cursor.fetchone()["id"] if wants_id else None
        return Cursor(cursor, lastrowid)

    def executemany(self, sql, rows):
        if not self.postgres:
            return self.raw.executemany(sql, rows)
        sql = sql.replace("%", "%%").replace("?", "%s")
        with self.raw.cursor() as cursor:
            cursor.executemany(sql, [tuple(row) for row in rows])
        return None

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()

    def begin_write(self):
        """Start a transaction that no other booking write can overlap (CRB-F-020)."""
        self.raw.commit()  # make sure no earlier transaction is still open
        if self.postgres:
            self.raw.execute("SELECT pg_advisory_xact_lock(%s)", (BOOKING_WRITE_LOCK,))
        else:
            self.raw.execute("BEGIN IMMEDIATE")

    def hours_between(self, later, earlier):
        """SQL for the number of hours from column `earlier` to column `later`."""
        if self.postgres:
            return (
                "(EXTRACT(EPOCH FROM (" + later + "::timestamp - " + earlier + "::timestamp)) / 3600.0)"
            )
        return "((julianday(" + later + ") - julianday(" + earlier + ")) * 24)"


def is_postgres():
    return bool(current_app.config.get("DATABASE_URL"))


def get_db():
    """Return the database connection for the current request."""
    if "db" not in g:
        url = current_app.config.get("DATABASE_URL")
        if url:
            if psycopg is None:
                raise RuntimeError("DATABASE_URL is set but psycopg is not installed")
            raw = psycopg.connect(url, row_factory=_row_factory)
            g.db = Connection(raw, postgres=True)
        else:
            raw = sqlite3.connect(current_app.config["DATABASE"])
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys = ON")
            g.db = Connection(raw, postgres=False)
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def schema_text(postgres):
    """schema.sql as text; for Postgres the two SQLite-only spellings are swapped."""
    with current_app.open_resource("schema.sql") as schema_file:
        text = schema_file.read().decode("utf8")
    if postgres:
        text = text.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        text = text.replace(
            "DEFAULT (datetime('now', 'localtime'))",
            "DEFAULT to_char(localtimestamp, 'YYYY-MM-DD HH24:MI:SS')",
        )
    return text


def init_db():
    """Create all tables (this wipes any old data)."""
    db = get_db()
    text = schema_text(db.postgres)
    if db.postgres:
        db.raw.execute(text)
        db.commit()
    else:
        db.raw.executescript(text)


def database_url_from_env(testing=False):
    """The Postgres address to use, or None for SQLite.

    The test suite reads CRB_TEST_DATABASE_URL, never DATABASE_URL, so running the tests can
    never wipe the production database.
    """
    return os.environ.get("CRB_TEST_DATABASE_URL" if testing else "DATABASE_URL") or None
