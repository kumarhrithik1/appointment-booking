"""
booking_service.py — Core booking logic.

Concurrency strategy
--------------------
Double-booking is prevented at TWO independent layers:

1. In-process lock (_slot_lock): A per-slot threading.Lock ensures only one
   request can execute the check-then-book sequence for a given slot at a time,
   even under concurrent HTTP requests in the same process.

2. Database UNIQUE constraint on appointments(slot_id) + slots.is_booked flag:
   Even if the in-process lock is bypassed (e.g. multiple processes / workers),
   the DB will reject a duplicate with an IntegrityError, which we surface as a
   409 Conflict.
"""

import uuid
import json
import threading
from datetime import datetime, date, timedelta

import pymysql

from app.models.database import get_db

_slot_locks = {}
_slot_locks_mutex = threading.Lock()


def _lock_for_slot(slot_id):
    with _slot_locks_mutex:
        if slot_id not in _slot_locks:
            _slot_locks[slot_id] = threading.Lock()
        return _slot_locks[slot_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_available_slots(from_date=None, days=7):
    """Return all non-booked slots for the next `days` days."""
    from app.models.database import _seed_slots
    conn = get_db()
    _seed_slots(conn)  # idempotent — only inserts missing rows

    start = from_date or date.today()
    end = start + timedelta(days=days)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, slot_date, start_time, end_time, is_booked
            FROM   slots
            WHERE  slot_date >= %s AND slot_date < %s
            ORDER  BY slot_date, start_time
            """,
            (start.isoformat(), end.isoformat()),
        )
        rows = cur.fetchall()

    return [_format_slot(r) for r in rows]


def book_appointment(slot_id, customer_name, customer_email, note=None):
    """
    Attempt to book a slot.
    Raises ValueError for invalid slot or already-booked slot.
    """
    lock = _lock_for_slot(slot_id)

    with lock:  # Layer 1: in-process serialisation per slot
        conn = get_db()

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM slots WHERE id = %s", (slot_id,))
            slot = cur.fetchone()

        if slot is None:
            raise ValueError("Slot not found.")

        if slot["is_booked"]:
            raise ValueError("Slot is already booked.")

        appt_id = str(uuid.uuid4())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE slots SET is_booked = 1 WHERE id = %s",
                    (slot_id,)
                )
                cur.execute(
                    """
                    INSERT INTO appointments
                        (id, slot_id, customer_name, customer_email, note, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'confirmed', %s)
                    """,
                    (appt_id, slot_id, customer_name, customer_email, note, now),
                )
                _enqueue_notification(cur, appt_id, customer_name, customer_email, slot)

            conn.commit()

        except pymysql.IntegrityError as e:
            conn.rollback()
            print("Integrity Error:", e)
            raise ValueError("Slot is already booked.")
        except Exception:
            conn.rollback()
            raise

    return _get_appointment(appt_id)


def cancel_appointment(appointment_id):
    """
    Cancel an appointment.
    Idempotent — safe to call multiple times.
    """
    conn = get_db()

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
        appt = cur.fetchone()

    if appt is None:
        raise ValueError("Appointment not found.")

    if appt["status"] == "cancelled":
        return _get_appointment(appointment_id)  # already cancelled, return as-is

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE appointments
                SET status = 'cancelled', cancelled_at = %s
                WHERE id = %s AND status = 'confirmed'
                """,
                (now, appointment_id),
            )
            cur.execute(
                "UPDATE slots SET is_booked = 0 WHERE id = %s",
                (appt["slot_id"],)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return _get_appointment(appointment_id)


def get_appointments(include_cancelled=False):
    """Return all appointments joined with slot info."""
    conn = get_db()

    query = """
        SELECT a.id, a.customer_name, a.customer_email, a.note,
               a.status, a.created_at, a.cancelled_at,
               s.slot_date, s.start_time, s.end_time
        FROM   appointments a
        JOIN   slots s ON s.id = a.slot_id
    """
    if not include_cancelled:
        query += " WHERE a.status = 'confirmed'"
    query += " ORDER BY s.slot_date, s.start_time"

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return [_format_appointment(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_appointment(appointment_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.id, a.customer_name, a.customer_email, a.note,
                   a.status, a.created_at, a.cancelled_at,
                   s.slot_date, s.start_time, s.end_time
            FROM   appointments a
            JOIN   slots s ON s.id = a.slot_id
            WHERE  a.id = %s
            """,
            (appointment_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError("Appointment not found.")

    return _format_appointment(row)


def _enqueue_notification(cur, appt_id, name, email, slot):
    """
    Insert notification row inside the same cursor/transaction as the appointment.
    This is the outbox pattern — notification is never silently lost.
    """
    payload = json.dumps({
        "to":         email,
        "name":       name,
        "date":       str(slot["slot_date"]),
        "start_time": _time_to_str(slot["start_time"]),
        "end_time":   _time_to_str(slot["end_time"]),
    })
    notif_id = str(uuid.uuid4())
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO notifications (id, appointment_id, type, status, payload, created_at)
        VALUES (%s, %s, 'confirmation', 'pending', %s, %s)
        """,
        (notif_id, appt_id, payload, now),
    )

def _time_to_str(value):
    """
    MySQL TIME columns are returned as datetime.timedelta by pymysql.
    Convert to HH:MM string so the rest of the app stays consistent.
    """
    if isinstance(value, str):
        return value[:5]
    total_seconds = int(value.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours:02d}:{minutes:02d}"


def _format_slot(row):
    return {
        "id":         row["id"],
        "slot_date":  str(row["slot_date"]),
        "start_time": _time_to_str(row["start_time"]),
        "end_time":   _time_to_str(row["end_time"]),
        "is_booked":  bool(row["is_booked"]),
    }


def _format_appointment(row):
    return {
        "id":             row["id"],
        "customer_name":  row["customer_name"],
        "customer_email": row["customer_email"],
        "note":           row["note"],
        "status":         row["status"],
        "created_at":     str(row["created_at"]),
        "cancelled_at":   str(row["cancelled_at"]) if row["cancelled_at"] else None,
        "slot_date":      str(row["slot_date"]),
        "start_time":     _time_to_str(row["start_time"]),
        "end_time":       _time_to_str(row["end_time"]),
    }