import datetime

from flask import Blueprint, request, jsonify, g

from db import db_cursor
from utils.auth_utils import login_required, sensor_api_key_required

bp = Blueprint("readings", __name__, url_prefix="/api")


def _status_for(decibel_value, max_decibel):
    """Colour-coded status used by the dashboard: green / yellow / red."""
    if max_decibel is None:
        return "unknown"
    if decibel_value <= max_decibel - 5:
        return "green"
    if decibel_value <= max_decibel:
        return "yellow"
    return "red"


def _find_active_threshold(cur, sensor_id, at_time):
    """Return the threshold row that applies to this sensor at the given
    time-of-day, handling periods that don't cross midnight (the common
    case for lecture/lab hours)."""
    at_time_str = at_time.strftime("%H:%M:%S")
    cur.execute(
        """SELECT * FROM alert_thresholds
           WHERE sensor_id=%s AND is_active=TRUE
             AND period_start <= %s AND period_end >= %s
           ORDER BY id LIMIT 1""",
        (sensor_id, at_time_str, at_time_str),
    )
    return cur.fetchone()


@bp.post("/readings")
@sensor_api_key_required
def ingest_reading():
    """Endpoint used by ESP8266 firmware (see simulator/simulate_sensors.py
    for a software stand-in) to push a single noise reading."""
    data = request.get_json(silent=True) or {}
    decibel_value = data.get("decibel_value")
    recorded_at_raw = data.get("recorded_at")

    if decibel_value is None:
        return jsonify({"error": "decibel_value is required"}), 400
    try:
        decibel_value = float(decibel_value)
    except (TypeError, ValueError):
        return jsonify({"error": "decibel_value must be numeric"}), 400

    if recorded_at_raw:
        try:
            recorded_at = datetime.datetime.fromisoformat(recorded_at_raw)
        except ValueError:
            recorded_at = datetime.datetime.utcnow()
    else:
        recorded_at = datetime.datetime.utcnow()

    with db_cursor(commit=True) as (conn, cur):
        cur.execute(
            "SELECT id, calibration_offset FROM sensor_nodes WHERE api_key=%s",
            (g.sensor_api_key,),
        )
        sensor = cur.fetchone()
        if not sensor:
            return jsonify({"error": "Unrecognized sensor API key"}), 401

        sensor_id = sensor["id"]
        calibrated_value = round(decibel_value + float(sensor["calibration_offset"]), 2)

        threshold = _find_active_threshold(cur, sensor_id, recorded_at.time())
        violation = bool(threshold and calibrated_value > float(threshold["max_decibel"]))

        cur.execute(
            """INSERT INTO noise_readings (sensor_id, decibel_value, recorded_at, violation_flag)
               VALUES (%s, %s, %s, %s)""",
            (sensor_id, calibrated_value, recorded_at, violation),
        )
        reading_id = cur.lastrowid

        cur.execute(
            "UPDATE sensor_nodes SET last_seen=%s WHERE id=%s",
            (recorded_at, sensor_id),
        )

        alert_created = False
        if violation:
            # Hysteresis / anti-chatter: only raise a new alert if there
            # isn't already a pending (un-acknowledged) one for this
            # threshold. Once an administrator acknowledges it, the next
            # violation is free to raise a fresh alert.
            cur.execute(
                "SELECT id FROM alert_logs WHERE threshold_id=%s AND status='pending' LIMIT 1",
                (threshold["id"],),
            )
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO alert_logs (threshold_id, sensor_id, reading_id, decibel_value, triggered_at, status)
                       VALUES (%s, %s, %s, %s, %s, 'pending')""",
                    (threshold["id"], sensor_id, reading_id, calibrated_value, recorded_at),
                )
                alert_created = True

    return jsonify({
        "reading_id": reading_id,
        "calibrated_decibel_value": calibrated_value,
        "violation": violation,
        "alert_created": alert_created,
    }), 201


@bp.get("/readings/latest")
@login_required
def latest_readings():
    """One most-recent reading per active sensor, with colour status --
    what the dashboard polls every few seconds."""
    with db_cursor() as (conn, cur):
        cur.execute("""
            SELECT s.id AS sensor_id, s.sensor_code, s.location, s.room_identifier, s.status,
                   r.decibel_value, r.recorded_at, r.violation_flag,
                   t.max_decibel
            FROM sensor_nodes s
            LEFT JOIN noise_readings r ON r.id = (
                SELECT id FROM noise_readings WHERE sensor_id = s.id ORDER BY recorded_at DESC LIMIT 1
            )
            LEFT JOIN alert_thresholds t ON t.sensor_id = s.id AND t.is_active = TRUE
                AND t.period_start <= CURTIME() AND t.period_end >= CURTIME()
            ORDER BY s.location
        """)
        rows = cur.fetchall()

    for row in rows:
        dv = float(row["decibel_value"]) if row["decibel_value"] is not None else None
        max_db = float(row["max_decibel"]) if row["max_decibel"] is not None else None
        row["status_colour"] = _status_for(dv, max_db) if dv is not None else "no-data"

    return jsonify({"readings": rows})


@bp.get("/readings/history")
@login_required
def reading_history():
    """Historical trend data for charts. Query params:
    sensor_id (required), range = 'hour' | 'day' | 'week' (default 'day')."""
    sensor_id = request.args.get("sensor_id", type=int)
    range_key = request.args.get("range", "day")

    if not sensor_id:
        return jsonify({"error": "sensor_id query parameter is required"}), 400

    interval_map = {"hour": "1 HOUR", "day": "1 DAY", "week": "7 DAY"}
    interval = interval_map.get(range_key, "1 DAY")

    with db_cursor() as (conn, cur):
        cur.execute(
            f"""SELECT decibel_value, recorded_at, violation_flag
                FROM noise_readings
                WHERE sensor_id=%s AND recorded_at >= NOW() - INTERVAL {interval}
                ORDER BY recorded_at ASC""",
            (sensor_id,),
        )
        rows = cur.fetchall()

    return jsonify({"sensor_id": sensor_id, "range": range_key, "readings": rows})
