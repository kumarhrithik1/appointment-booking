# BookSlot — Appointment Booking System

A full-stack appointment booking system built with Flask (Python) and React (Create React App). Users can browse available 30-minute time slots for the next 7 days, book appointments, and cancel them.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Data Model](#data-model)
4. [API Reference](#api-reference)
5. [Architectural Decisions](#architectural-decisions)
6. [Trade-offs](#trade-offs)
7. [Known Limitations](#known-limitations)
8. [Future Improvements](#future-improvements)
9. [AI Tools Usage](#ai-tools-usage)

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| MySQL | 8.0+ |

---

### Step 1 — MySQL setup

```sql
CREATE DATABASE appointments;
```

---

### Step 2 — Backend

```bash
cd backend

# Install Python dependencies
pip install Flask PyMySQL cryptography python-dotenv

# Create your .env file
```

Edit `.env` with your credentials:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_passsword
DB_NAME=appointments

ALLOWED_ORIGIN=http://localhost:5173
```

```bash
# Start the backend (tables and seed data are auto-created on first run)
cd backend
python main.py
# Listening on http://localhost:8000
```

Verify it is running:

```bash
curl http://localhost:8000/api/health
# {"status": "ok"}
```

---

### Step 3 — Frontend

```bash
cd frontend

npm install
npm start
# Opens http://localhost:3000
```

The frontend uses CRA's built-in proxy (configured in `package.json`) to forward all `/api/*` requests to `http://localhost:8000`. No CORS configuration or extra env variable is needed for local development.

---

### Environment Variables

**Backend — `backend/.env`**


DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_passsword
DB_NAME=appointments

ALLOWED_ORIGIN=http://localhost:5173

**Frontend — `frontend/config.js` (production only)**

| Variable | Description |
|----------|-------------|
| `REACT_APP_API_URL` | Full API base URL (e.g. `https://api.yoursite.com`) |

Leave `REACT_APP_API_URL` unset in development — the CRA proxy handles routing automatically.

---

## Project Structure

```
appointment-booking/
├── backend/
│   ├── main.py                          # Entrypoint — starts Flask on port 8000
│   ├── requirements.txt
│   ├── .env
│   └── app/
│       ├── __init__.py                  # App factory: CORS, blueprints, DB init, worker
│       ├── models/
│       │   └── database.py              # MySQL connection, schema DDL, slot seeding
│       ├── routes/
│       │   └── routes.py                # 5 HTTP endpoints (thin validation layer)
│       ├── services/
│       │   └── booking_service.py       # All booking logic + concurrency control
│       └── workers/
│           └── notification_worker.py   # Outbox-pattern daemon thread
└── frontend/
    ├── package.json                     # CRA + proxy: "http://localhost:8000"
    ├── public/
    │   └── index.html
    └── src/
        ├── index.js                     # CRA entry point
        ├── App.js                       # Root component + state management
        ├── api.js                       # All fetch() calls in one place
        ├── config.js                    # Centralised BASE_URL for API
        └── components/
            ├── SlotGrid.js / .css
            ├── BookingModal.js / .css   # Uses shadcn Dialog + Button
            ├── AppointmentList.js / .css
            ├── Toast.js / .css
            └── ui/
                ├── Button.js / .css     # shadcn Button (cva + Radix Slot)
                └── Dialog.js / .css     # shadcn Dialog (Radix Dialog primitive)
```

---

## Data Model

### `slots`

Pre-seeded time slots. Generated for the next 7 days (Mon–Sat, 09:00–17:00, 30-minute increments) on every startup and on every `GET /slots` call via idempotent `INSERT IGNORE`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) | UUID primary key |
| `slot_date` | DATE | Calendar date |
| `start_time` | TIME | e.g. `09:00` |
| `end_time` | TIME | e.g. `09:30` |
| `is_booked` | TINYINT(1) | `0` = free, `1` = taken |

Unique constraint: `(slot_date, start_time)` — prevents duplicate slots.

---

### `appointments`

One row per booking. One-to-one with `slots` enforced by `UNIQUE KEY uq_appointment_slot (slot_id)`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) | UUID primary key |
| `slot_id` | VARCHAR(36) | FK → `slots.id`, UNIQUE |
| `customer_name` | VARCHAR(255) | Required |
| `customer_email` | VARCHAR(255) | Required |
| `note` | TEXT | Optional |
| `status` | VARCHAR(20) | `confirmed` or `cancelled` |
| `created_at` | DATETIME | UTC |
| `cancelled_at` | DATETIME | UTC, nullable |

The `UNIQUE` constraint on `slot_id` is the database-level hard guard against double bookings. Even if two requests bypass the application-level lock (e.g. multi-process deployment), MySQL rejects the second `INSERT` with an `IntegrityError`.

---

### `notifications`

Outbox table — one row per notification, written atomically with its parent appointment.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) | UUID primary key |
| `appointment_id` | VARCHAR(36) | FK → `appointments.id` |
| `type` | VARCHAR(50) | `confirmation` |
| `status` | VARCHAR(20) | `pending`, `sent`, `failed`, `skipped` |
| `payload` | TEXT | JSON: `{to, name, date, start_time, end_time}` |
| `attempts` | INT | Delivery attempt count (max 3) |
| `last_attempted` | DATETIME | Nullable |
| `created_at` | DATETIME | UTC |

---

## API Reference

All endpoints are under the `/api/` prefix.

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| GET | `/slots?available=true` | Available slots for next 7 days | 200 |
| GET | `/appointments?include_cancelled=false` | List appointments | 200 |
| POST | `/appointments` | Create a booking | 201 |
| POST | `/appointments/:id/cancel` | Cancel a booking (idempotent) | 200 |
| GET | `/health` | Liveness check | 200 |

**POST /api/appointments — request body**

```json
{
  "slot_id":        "6f3a1b...",
  "customer_name":  "Jane Smith",
  "customer_email": "jane@example.com",
  "note":           "Optional note"
}
```

**Error format:** `{"error": "Human-readable message"}` with HTTP status 400 (bad input), 404 (not found), 409 (conflict / already booked), or 500 (server error).

---

## Architectural Decisions

### 1. Two-layer double-booking prevention

Double booking is prevented at two independent layers so that neither failure mode can allow a duplicate booking:

**Layer 1 — Per-slot `threading.Lock` (in-process)**
`_lock_for_slot(slot_id)` returns a `threading.Lock` keyed on the slot UUID. The lock is held for the entire read-validate-write-commit sequence. This ensures that two concurrent HTTP requests in the same process cannot both pass the `is_booked = 0` check before either commits.

**Layer 2 — `UNIQUE KEY uq_appointment_slot (slot_id)` (database)**
Even if the application lock is bypassed (multiple processes, a bug), MySQL rejects the second `INSERT INTO appointments` with an `IntegrityError`, which the service catches and converts to a 409 Conflict response.

Neither layer alone is sufficient. The application lock fails under multi-worker deployment. The DB constraint alone leaves a race window between `SELECT` and `INSERT`.

### 2. Transactional Outbox Pattern for notifications

The `notifications` row is written inside the same `conn.cursor()` / `conn.commit()` as the appointment row. This gives an atomic guarantee: either both the appointment and its notification row are committed, or neither is. The background worker then polls for `status = 'pending'` rows every 5 seconds. If the worker crashes, the pending rows survive and are retried. The worker also checks whether the appointment was cancelled before sending — if so, it marks the notification `skipped` instead of sending a confirmation for a cancelled booking.

### 3. Thread-local MySQL connections

Each Flask worker thread gets its own MySQL connection via `threading.local()`. This avoids connection pool complexity (no `mysql-connector-python` pool, no SQLAlchemy pool config). `conn.ping(reconnect=True)` automatically re-establishes connections that went idle. The trade-off is that connection count equals thread count, but for a development/small-production deployment this is entirely acceptable.

### 4. Idempotent cancellation

`cancel_appointment` first checks `if appt["status"] == "cancelled"` and returns the current state unchanged rather than raising an error. The `UPDATE` query also uses `WHERE status = 'confirmed'` as a second guard so that concurrent cancel calls for the same appointment cannot both execute the `UPDATE`. Idempotency means the client can safely retry a cancel request without risk of error.

### 5. Slot seeding called on every `GET /slots`

`_seed_slots()` uses `INSERT IGNORE` so it only inserts rows that do not already exist — it is effectively a no-op for slots that are already there. Calling it on every `GET /slots` means the server always serves a fresh 7-day window regardless of how long it has been running, without requiring a cron job or scheduler.

### 6. shadcn/ui in Create React App without path aliases

`Button` and `Dialog` components use Radix UI primitives (`@radix-ui/react-dialog`, `@radix-ui/react-slot`) for accessibility (focus trapping, Escape-to-close, `aria-modal`, `role="dialog"`). `class-variance-authority` (cva) generates consistent variant/size class names. All `@/` path aliases were removed and replaced with explicit relative imports so the project works with CRA's default Webpack configuration — no `craco`, no `webpack.config.js` override needed.

### 7. Centralised API config (`config.js`)

All API calls read `config.BASE_URL`. In development it is an empty string and CRA's proxy handles routing. For production, only `REACT_APP_API_URL` needs to change — no other file is touched. This is the single point of truth for the API location.

---

## Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| `threading.Lock` per slot | Zero dependencies, simple reasoning | Fails under multi-process deployment (Gunicorn `-w 4`) |
| DB-polling notification worker | No message broker needed | Up to 5s notification delay; won't scale at high volume |
| No ORM | Explicit SQL, easy to debug | No migration tooling; more verbose |
| `INSERT IGNORE` for seeding | Idempotent, no startup errors | MySQL-only syntax |
| Thread-local connections | No pool config needed | Connection per thread; no reuse across requests |
| Seeding on every `GET /slots` | Always fresh 7-day window | Minor overhead per request |
| No authentication | Simpler to demo and test | Anyone can cancel any appointment if they know its ID |
| CRA instead of Vite | Standard tooling, zero config issues | Slower build; CRA is in maintenance mode |

---

## Known Limitations

1. **In-process lock only.** The `threading.Lock` does not work across multiple server processes. A multi-worker deployment would require `SELECT GET_LOCK()` (MySQL advisory lock) or Redis `SETNX`.

2. **Slot window is startup-scoped.** Slots are seeded from today's date at startup and on each `GET /slots` call. However a long-running server that is not restarted will correctly generate new slots on each request because seeding is called there — but only if `GET /slots` is called. Without any requests, slots will not self-refresh.

3. **No authentication.** Any client can cancel any appointment by ID. There is no ownership or session concept.

4. **Notification delivery is stubbed.** `_send_notification()` logs to console only. No email is actually sent.

5. **No pagination.** `GET /appointments` returns all rows. This degrades with a large dataset.

6. **MySQL-specific.** `INSERT IGNORE` and the connection URL format are not portable to PostgreSQL.

7. **No HTTPS in development.** Production deployment needs TLS termination (nginx, Caddy, etc.).

---

## Future Improvements

With more time, the following would be prioritised in order:

1. **Database advisory lock** — Replace `threading.Lock` with `SELECT GET_LOCK(slot_id, 5)` so booking safety holds across multiple processes without needing Redis.

2. **Real email delivery** — Swap the `_send_notification()` stub with SendGrid or AWS SES. The outbox infrastructure is already in place; only the send function body needs to change.

3. **User authentication** — JWT-based auth so each user can only see and cancel their own appointments.

4. **APScheduler for daily slot seeding** — A background job that runs `_seed_slots()` at midnight so the 7-day window stays current indefinitely regardless of request traffic.

5. **Celery + Redis for notifications** — Replace the 5-second DB-poll loop with a proper task queue for lower latency, retries with backoff, and horizontal scalability.

6. **Alembic migrations** — Replace `CREATE TABLE IF NOT EXISTS` with versioned migration files for safe schema evolution.

7. **Full test suite** — Unit tests for `booking_service.py` (including concurrent booking tests with `concurrent.futures.ThreadPoolExecutor`), integration tests against a test database, and React Testing Library tests for frontend components.

8. **Docker Compose** — A single `docker-compose.yml` that starts MySQL, the Flask backend, and the React dev server together so the project runs with one command.

9. **Pagination** — `?page=&per_page=` on list endpoints.

10. **Slot duration configuration** — Allow 15, 30, or 60-minute slots rather than hardcoding 30 minutes.

---

## AI Tools Usage

### Where AI tools were used

Claude (Anthropic) was used as a development assistant throughout this project:

### How the generated outputs were validated

All AI-generated code was reviewed before use:

- **Backend logic** — every function was read line-by-line. The concurrency strategy was traced manually against MySQL's default isolation level.
- **SQL** — all queries were checked against the schema definitions. `INSERT IGNORE` behaviour was verified against the MySQL 8.0 reference manual.
- **Frontend imports** — each file's import paths were checked against the actual directory tree.
- **API proxy** — the CRA proxy behaviour with and without `Content-Type` on GET requests was confirmed by reading the `http-proxy-middleware` documentation.
- **README commands** — every `pip install`, and `npm` command was checked against the actual file structure before being written here.