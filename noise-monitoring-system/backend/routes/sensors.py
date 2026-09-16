import secrets

from flask import Blueprint, request, jsonify, g

from db import db_cursor
from utils.auth_utils import login_required, roles_required

bp = Blueprint("sensors", __name__, url_prefix="/api/sensors")


@bp.get("")
@login_required
def list_sensors():
    with db_cursor() as (conn, cur):
        cur.execute("""
            SELECT id, sensor_code, location, room_identifier, calibration_offset,
                   status, last_seen, created_at
            FROM sensor_nodes
            ORDER BY location
        """)
        sensors = cur.fetchall()
    return jsonify({"sensors": sensors})


@bp.post("")
@login_required
@roles_required("administrator", "system_admin")
def create_sensor():
    data = request.get_json(silent=True) or {}
    sensor_code = (data.get("sensor_code") or "").strip()
    location = (data.get("location") or "").strip()
    room_identifier = (data.get("room_identifier") or "").strip()
    calibration_offset = data.get("calibration_offset", 0)

    if not sensor_code or not location or not room_identifier:
        return jsonify({"error": "sensor_code, location and room_identifier are required"}), 400

    api_key = secrets.token_hex(16)

    with db_cursor(commit=True) as (conn, cur):
        cur.execute("SELECT id FROM sensor_nodes WHERE sensor_code=%s", (sensor_code,))
        if cur.fetchone():
            return jsonify({"error": "sensor_code already exists"}), 409

        cur.execute(
            """INSERT INTO sensor_nodes (sensor_code, api_key, location, room_identifier, calibration_offset)
               VALUES (%s, %s, %s, %s, %s)""",
            (sensor_code, api_key, location, room_identifier, calibration_offset),
        )
        sensor_id = cur.lastrowid

    return jsonify({
        "id": sensor_id,
        "sensor_code": sensor_code,
        "api_key": api_key,  # shown once so it can be flashed onto the firmware
        "location": location,
        "room_identifier": room_identifier,
    }), 201


@bp.patch("/<int:sensor_id>")
@login_required
@roles_required("administrator", "system_admin")
def update_sensor(sensor_id):
    data = request.get_json(silent=True) or {}
    fields, values = [], []

    for key in ("location", "room_identifier", "status"):
        if key in data:
            fields.append(f"{key}=%s")
            values.append(data[key])
    if "calibration_offset" in data:
        fields.append("calibration_offset=%s")
        values.append(data["calibration_offset"])

    if not fields:
        return jsonify({"error": "No updatable fields supplied"}), 400

    values.append(sensor_id)
    with db_cursor(commit=True) as (conn, cur):
        cur.execute(f"UPDATE sensor_nodes SET {', '.join(fields)} WHERE id=%s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Sensor not found"}), 404

    return jsonify({"message": "Sensor updated"})


@bp.get("/<int:sensor_id>")
@login_required
def get_sensor(sensor_id):
    with db_cursor() as (conn, cur):
        cur.execute("SELECT * FROM sensor_nodes WHERE id=%s", (sensor_id,))
        sensor = cur.fetchone()
    if not sensor:
        return jsonify({"error": "Sensor not found"}), 404
    sensor.pop("api_key", None)
    return jsonify({"sensor": sensor})
