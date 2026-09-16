import datetime

from flask import Blueprint, request, jsonify, g

from db import db_cursor
from utils.auth_utils import login_required, roles_required

bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@bp.get("")
@login_required
def list_alerts():
    status = request.args.get("status")  # 'pending' | 'acknowledged' | None (all)
    with db_cursor() as (conn, cur):
        query = """
            SELECT a.*, s.sensor_code, s.location, s.room_identifier, t.max_decibel, t.label
            FROM alert_logs a
            JOIN sensor_nodes s ON s.id = a.sensor_id
            JOIN alert_thresholds t ON t.id = a.threshold_id
        """
        params = ()
        if status in ("pending", "acknowledged"):
            query += " WHERE a.status=%s"
            params = (status,)
        query += " ORDER BY a.triggered_at DESC LIMIT 200"
        cur.execute(query, params)
        rows = cur.fetchall()
    return jsonify({"alerts": rows})


@bp.post("/<int:alert_id>/acknowledge")
@login_required
@roles_required("administrator", "system_admin")
def acknowledge_alert(alert_id):
    now = datetime.datetime.utcnow()
    user_id = g.current_user["user_id"]

    with db_cursor(commit=True) as (conn, cur):
        cur.execute(
            """UPDATE alert_logs SET status='acknowledged', acknowledged_at=%s, user_id=%s
               WHERE id=%s AND status='pending'""",
            (now, user_id, alert_id),
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Alert not found or already acknowledged"}), 404

    return jsonify({"message": "Alert acknowledged"})
