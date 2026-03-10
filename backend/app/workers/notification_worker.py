"""
notification_worker.py — Background notification processor.

Design: Transactional Outbox Pattern
--------------------------------------
Notifications are written to the `notifications` table inside the same
transaction that creates the appointment. This means:

  - We can never book an appointment and silently lose its notification.
  - If the worker crashes, pending rows survive in the DB and are retried
    on restart (at-least-once delivery).

The worker is a daemon thread polling the DB every few seconds.
"""

import json
import threading
import time
import logging
from datetime import datetime

from app.models.database import get_db

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 5


def _send_notification(payload):
    """
    Simulate sending a confirmation email.
    In production: swap this body for SendGrid, SES, SMTP, etc.
    """
    logger.info(
        "[NOTIFICATION SENT] To: %s (%s) | Appointment: %s %s–%s",
        payload.get("to"),
        payload.get("name"),
        payload.get("date"),
        payload.get("start_time"),
        payload.get("end_time"),
    )


def _process_pending():
    """Pick up pending notifications and attempt delivery."""
    conn = get_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.id, n.appointment_id, n.payload, n.attempts
            FROM   notifications n
            WHERE  n.status = 'pending'
              AND  n.attempts < %s
            ORDER  BY n.created_at
            LIMIT  10
            """,
            (MAX_ATTEMPTS,),
        )
        pending = cur.fetchall()

    for row in pending:
        notif_id = row["id"]

        try:
            payload = json.loads(row["payload"])

            # Skip if the appointment was cancelled before we sent the notification
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM appointments WHERE id = %s",
                    (row["appointment_id"],),
                )
                appt = cur.fetchone()

            if appt and appt["status"] == "cancelled":
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE notifications SET status = 'skipped', last_attempted = %s WHERE id = %s",
                        (now, notif_id),
                    )
                conn.commit()
                continue

            _send_notification(payload)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications
                    SET status = 'sent', attempts = attempts + 1, last_attempted = %s
                    WHERE id = %s
                    """,
                    (now, notif_id),
                )
            conn.commit()

        except Exception as exc:
            logger.warning(
                "Notification %s failed (attempt %d): %s",
                notif_id, row["attempts"] + 1, exc
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications
                    SET attempts = attempts + 1,
                        last_attempted = %s,
                        status = CASE WHEN attempts + 1 >= %s THEN 'failed' ELSE 'pending' END
                    WHERE id = %s
                    """,
                    (now, MAX_ATTEMPTS, notif_id),
                )
            conn.commit()


def run_worker():
    """Entry point for the background thread. Polls DB every POLL_INTERVAL_SECONDS."""
    logger.info("Notification worker started (poll interval: %ds).", POLL_INTERVAL_SECONDS)
    while True:
        try:
            _process_pending()
        except Exception as exc:
            logger.error("Worker loop error: %s", exc)
        time.sleep(POLL_INTERVAL_SECONDS)


def start_worker_thread():
    """Launch the worker as a daemon thread alongside Flask."""
    t = threading.Thread(target=run_worker, daemon=True, name="NotificationWorker")
    t.start()
    return t