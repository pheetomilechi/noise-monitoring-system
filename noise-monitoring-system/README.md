# Real-Time Noise Monitoring System

A working implementation of the system described in the project write-up
(Faculty of Artificial Intelligence, Taraba State University), rebuilt
with a **Python (Flask) backend**, a **MySQL** database, and a
**vanilla HTML5 / CSS / JavaScript** frontend.

It implements all six modules from the design: Sensor Deployment &
Data Acquisition, Data Transmission & Communication, Data Processing &
Storage, Real-Time Visualization & Dashboard, Alert & Notification, and
Reporting & Analytics — plus authentication and role-based access
(student / administrator).

Since physical LM393 + ESP8266 hardware isn't available here, a
**software simulator** (`simulator/simulate_sensors.py`) stands in for
the sensor firmware, posting to the exact same `/api/readings`
endpoint real hardware would use. Swap it out for real firmware at any
time — the backend doesn't know the difference.

## 1. Prerequisites

- Python 3.9+
- MySQL 8.0+ (or MariaDB 10.5+) running locally or reachable over the network

## 2. Set up the database

```bash
mysql -u root -p < backend/schema.sql
```

This creates the `noise_monitoring` database, all five tables
(`users`, `sensor_nodes`, `noise_readings`, `alert_thresholds`,
`alert_logs`), and seeds three demo sensor nodes with matching
default thresholds.

## 3. Set up the backend

```bash
cd backend
python -m venv venv && source venv/Scripts/activate   # optional but recommended
pip install -r requirements.txt

# point the app at your MySQL instance (defaults shown)
export NMS_DB_HOST=127.0.0.1
export NMS_DB_USER=root
export NMS_DB_PASSWORD=yourpassword
export NMS_DB_NAME=noise_monitoring
export NMS_JWT_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))")

# create the first administrator account
python seed_admin.py admin@fai.edu.ng "Faculty Admin" "Admin123!"

# run the server (also serves the frontend at the same origin)
python app.py
```

The backend starts on `http://localhost:5000` and serves the frontend
from `../frontend` at the same address, so you can open
`http://localhost:5000` directly — no separate web server needed.
(You can still host `frontend/` on any static file server if you
prefer; just point `API_BASE` in `frontend/js/api.js` at the backend.)

## 4. Feed it data

In a second terminal:

```bash
cd simulator
pip install requests   # already in backend/requirements.txt if you reused that venv
python simulate_sensors.py --server http://localhost:5000
```

This posts realistic, slowly-drifting decibel readings for the three
seeded sensors every 5 seconds, with occasional spikes so you can
watch alerts fire live on the dashboard.

## 5. Use the system

1. Open `http://localhost:5000` in a browser.
2. Create an account (or sign in as the administrator you seeded).
3. Student dashboards show live colour-coded noise levels and
   historical trends. Administrator dashboards additionally show
   pending alerts (with an Acknowledge action) and threshold
   configuration.

## Project structure

```
noise-monitoring-system/
├── backend/
│   ├── app.py               Flask app + route registration
│   ├── config.py             Environment-driven configuration
│   ├── db.py                 PyMySQL connection/cursor helper
│   ├── schema.sql            MySQL DDL + seed data
│   ├── seed_admin.py         Creates the first admin account
│   ├── requirements.txt
│   ├── routes/
│   │   ├── auth.py           Register / login / me
│   │   ├── sensors.py        Sensor node CRUD
│   │   ├── readings.py       Ingestion + threshold evaluation + history
│   │   ├── thresholds.py     Threshold configuration CRUD
│   │   ├── alerts.py         Alert listing + acknowledgement
│   │   └── analytics.py      Summary stats, violation reports
│   └── utils/auth_utils.py   JWT issuing/verification, RBAC decorators
├── simulator/
│   └── simulate_sensors.py   Software stand-in for ESP8266 firmware
└── frontend/
    ├── index.html             Sign in / register
    ├── dashboard.html          Live dashboard
    ├── css/style.css
    └── js/{api,auth,dashboard,charts}.js
```

## How the design maps onto the write-up's ERD

| ERD entity        | Table              | Notes |
|--------------------|--------------------|-------|
| User               | `users`             | role: student / administrator / system_admin |
| SensorNode         | `sensor_nodes`      | `api_key` added so firmware authenticates without a user login |
| NoiseReading       | `noise_readings`    | `violation_flag` set at ingestion time |
| AlertThreshold     | `alert_thresholds`  | per-sensor, per-time-period, with `hysteresis_db` |
| AlertLog           | `alert_logs`        | `status` pending/acknowledged drives the hysteresis logic |

**Hysteresis logic**: rather than re-alerting on every reading while a
space stays noisy, a new `alert_logs` row is only created if no
`pending` alert already exists for that threshold. Once an
administrator acknowledges it, the next violation is free to raise a
fresh alert — this is the same anti-chattering behaviour described in
Section 3.2.2.3 of the write-up, implemented without needing extra
in-memory state.

## Notes on the technology swap

The original write-up specifies a Laravel/PHP backend; this build
follows the same ERD, module boundaries, and MySQL schema but
implements the backend in Flask (Python) as requested, with the
frontend built directly in HTML5/CSS/JavaScript (Chart.js for graphs)
rather than through a template engine. Email/SMS notification hooks
are stubbed as a configuration surface (`config.py`) so they can be
wired to a real provider (e.g. SMTP + Twilio) without changing the
alerting logic.
