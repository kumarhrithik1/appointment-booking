"""
database.py — MySQL connection layer.

Uses pymysql directly (no ORM) with a simple thread-local connection.
Set DATABASE Configuration in .env before running.
"""

import os
import re
import threading
import uuid
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, unquote
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

_DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

_local = threading.local()


def get_db():
    """
    Return a thread-local MySQL connection.
    Reconnects automatically if the connection was dropped.
    """
    conn = getattr(_local, "conn", None)

    if conn is None:
        _local.conn = pymysql.connect(**_DB_CONFIG)
        return _local.conn

    # ping() with reconnect=True re-establishes a stale connection
    try:
        conn.ping(reconnect=True)
    except Exception:
        _local.conn = pymysql.connect(**_DB_CONFIG)

    return _local.conn


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

CREATE_SLOTS_TABLE = """
CREATE TABLE IF NOT EXISTS slots (
    id          VARCHAR(36)  PRIMARY KEY,
    slot_date   DATE         NOT NULL,
    start_time  TIME         NOT NULL,
    end_time    TIME         NOT NULL,
    is_booked   TINYINT(1)   NOT NULL DEFAULT 0,
    UNIQUE KEY uq_slot (slot_date, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_APPOINTMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS appointments (
    id              VARCHAR(36)  PRIMARY KEY,
    slot_id         VARCHAR(36)  NOT NULL,
    customer_name   VARCHAR(255) NOT NULL,
    customer_email  VARCHAR(255) NOT NULL,
    note            TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'confirmed',
    created_at      DATETIME     NOT NULL,
    cancelled_at    DATETIME,
    KEY idx_slot_id (slot_id),
    CONSTRAINT fk_appt_slot FOREIGN KEY (slot_id) REFERENCES slots (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_NOTIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS notifications (
    id              VARCHAR(36)  PRIMARY KEY,
    appointment_id  VARCHAR(36)  NOT NULL,
    type            VARCHAR(50)  NOT NULL DEFAULT 'confirmation',
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
    payload         TEXT         NOT NULL,
    attempts        INT          NOT NULL DEFAULT 0,
    last_attempted  DATETIME,
    created_at      DATETIME     NOT NULL,
    CONSTRAINT fk_notif_appt FOREIGN KEY (appointment_id) REFERENCES appointments (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def init_db():
    """
    Create tables and seed slots for the next 7 days.
    Idempotent — safe to call on every startup.
    """
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(CREATE_SLOTS_TABLE)
        cur.execute(CREATE_APPOINTMENTS_TABLE)
        cur.execute(CREATE_NOTIFICATIONS_TABLE)
    conn.commit()
    _seed_slots(conn)


def _seed_slots(conn):
    """
    Ensure time slots exist for the next 7 days.
    Slots: 09:00–17:00 in 30-minute increments, Mon–Sat.
    Existing slots are left untouched (INSERT IGNORE).
    """
    today = date.today()
    slot_times = _generate_slot_times("09:00", "17:00", 30)

    with conn.cursor() as cur:
        for day_offset in range(7):
            slot_date = today + timedelta(days=day_offset)
            if slot_date.weekday() == 6:  # skip Sunday
                continue
            for start, end in slot_times:
                slot_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT IGNORE INTO slots (id, slot_date, start_time, end_time)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (slot_id, slot_date.isoformat(), start, end),
                )
    conn.commit()


def _generate_slot_times(start: str, end: str, interval_minutes: int):
    """Generate (start, end) time string pairs between start and end."""
    fmt = "%H:%M"
    current = datetime.strptime(start, fmt)
    end_dt  = datetime.strptime(end, fmt)
    pairs = []
    while current < end_dt:
        nxt = current + timedelta(minutes=interval_minutes)
        if nxt <= end_dt:
            pairs.append((current.strftime(fmt), nxt.strftime(fmt)))
        current = nxt
    return pairs