import json

from flask import Blueprint, request, jsonify

from db import db_cursor
from utils.auth_utils import login_required, roles_required

bp = Blueprint("thresholds", __name__, url_prefix="/api/thresholds")


@bp.get("")
@login_required
def list_thresholds():
    sensor_id = request.args.get("sensor_id", type=int)
    with db_cursor() as (conn, cur):
        if sensor_id:
            cur.execute(
                """SELECT t.*, s.sensor_code, s.location FROM alert_thresholds t
                   JOIN sensor_nodes s ON s.id = t.sensor_id
                   WHERE t.sensor_id=%s ORDER BY t.period_start""",
                (sensor_id,),
            )
        else:
            cur.execute(
                """SELECT t.*, s.sensor_code, s.location FROM alert_thresholds t
                   JOIN sensor_nodes s ON s.id = t.sensor_id
                   ORDER BY s.location, t.period_start"""
            )
        rows = cur.fetchall()
    return jsonify({"thresholds": rows})


@bp.post("")
@login_required
@roles_required("administrator", "system_admin")
def create_threshold():
    data = request.get_json(silent=True) or {}
    required = ["sensor_id", "max_decibel"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    with db_cursor(commit=True) as (conn, cur):
        cur.execute(
            """INSERT INTO alert_thresholds
               (sensor_id, label, max_decibel, hysteresis_db, period_start, period_end, notification_recipients)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                data["sensor_id"],
                data.get("label", "Custom threshold"),
                data["max_decibel"],
                data.get("hysteresis_db", 3.0),
                data.get("period_start", "00:00:00"),
                data.get("period_end", "23:59:59"),
                json.dumps(data.get("notification_recipients", [])),
            ),
        )
        threshold_id = cur.lastrowid

    return jsonify({"id": threshold_id, "message": "Threshold created"}), 201


@bp.patch("/<int:threshold_id>")
@login_required
@roles_required("administrator", "system_admin")
def update_threshold(threshold_id):
    data = request.get_json(silent=True) or {}
    fields, values = [], []

    for key in ("label", "max_decibel", "hysteresis_db", "period_start", "period_end", "is_active"):
        if key in data:
            fields.append(f"{key}=%s")
            values.append(data[key])
    if "notification_recipients" in data:
        fields.append("notification_recipients=%s")
        values.append(json.dumps(data["notification_recipients"]))

    if not fields:
        return jsonify({"error": "No updatable fields supplied"}), 400

    values.append(threshold_id)
    with db_cursor(commit=True) as (conn, cur):
        cur.execute(f"UPDATE alert_thresholds SET {', '.join(fields)} WHERE id=%s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Threshold not found"}), 404

    return jsonify({"message": "Threshold updated"})


@bp.delete("/<int:threshold_id>")
@login_required
@roles_required("administrator", "system_admin")
def delete_threshold(threshold_id):
    with db_cursor(commit=True) as (conn, cur):
        cur.execute("DELETE FROM alert_thresholds WHERE id=%s", (threshold_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Threshold not found"}), 404
    return jsonify({"message": "Threshold deleted"})
