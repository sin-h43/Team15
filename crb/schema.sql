DROP TABLE IF EXISTS outbox;
DROP TABLE IF EXISTS attendees;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS maintenance_blocks;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('employee', 'admin', 'auditor')),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);

CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    equipment TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

-- status: held (2-minute checkout hold), confirmed, cancelled, expired (hold ran out)
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('held', 'confirmed', 'cancelled', 'expired')),
    hold_expires_at TEXT,
    series_id INTEGER,
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE attendees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    UNIQUE (booking_id, user_id)
);

CREATE TABLE maintenance_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms (id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Emails are saved here instead of being sent (a real mail server is a later swap).
CREATE TABLE outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_username TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);