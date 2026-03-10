"""
routes.py — HTTP API surface.

Thin layer: validate input, delegate to booking_service, return JSON.
All business logic lives in the service; routes just translate HTTP ↔ domain.
"""

from flask import Blueprint, request, jsonify
from app.services.booking_service import (
    get_available_slots,
    book_appointment,
    cancel_appointment,
    get_appointments,
)
from datetime import date

api = Blueprint("api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

@api.route("/slots", methods=["GET"])
def slots():
    """
    GET /api/slots
    Returns all slots for the next 7 days.
    Query param: ?available=true  → only unbooked slots (default: all)
    """
    available_only = request.args.get("available", "true").lower() == "true"
    all_slots = get_available_slots()

    if available_only:
        result = [s for s in all_slots if not s["is_booked"]]
    else:
        result = all_slots

    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@api.route("/appointments", methods=["GET"])
def list_appointments():
    """
    GET /api/appointments
    Query param: ?include_cancelled=true
    """
    include_cancelled = request.args.get("include_cancelled", "false").lower() == "true"
    return jsonify(get_appointments(include_cancelled=include_cancelled)), 200


@api.route("/appointments", methods=["POST"])
def create_appointment():
    """
    POST /api/appointments
    Body (JSON):
      {
        "slot_id":        "<uuid>",
        "customer_name":  "Jane Smith",
        "customer_email": "jane@example.com",
        "note":           "Optional note"   // optional
      }
    """
    body = request.get_json(silent=True) or {}
    print(body)

    # Input validation
    required = ["slot_id", "customer_name", "customer_email"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if "@" not in body["customer_email"]:
        return jsonify({"error": "Invalid email address."}), 400

    try:
        appt = book_appointment(
            slot_id=body["slot_id"],
            customer_name=body["customer_name"].strip(),
            customer_email=body["customer_email"].strip().lower(),
            note=body.get("note"),
        )
        return jsonify(appt), 201

    except ValueError as exc:
        # Business rule violation (slot taken, not found, etc.)
        return jsonify({"error": str(exc)}), 409

    except Exception as exc:
        return jsonify({"error": "Unexpected server error.", "detail": str(exc)}), 500


@api.route("/appointments/<appointment_id>/cancel", methods=["POST"])
def cancel(appointment_id: str):
    """
    POST /api/appointments/<id>/cancel
    Idempotent — safe to call multiple times.
    """
    try:
        appt = cancel_appointment(appointment_id)
        return jsonify(appt), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": "Unexpected server error.", "detail": str(exc)}), 500


# ---------------------------------------------------------------------------
# Health / diagnostics
# ---------------------------------------------------------------------------

@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200