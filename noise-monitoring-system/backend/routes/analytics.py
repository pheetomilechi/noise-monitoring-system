from flask import Blueprint, request, jsonify

from db import db_cursor
from utils.auth_utils import login_required, roles_required

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.get("/summary")
@login_required
def summary():
    """High-level numbers for the administrator dashboard: sensors
    online, today's average/peak levels, and pending violation count."""
    with db_cursor() as (conn, cur):
        cur.execute("SELECT COUNT(*) AS total, SUM(status='active') AS active FROM sensor_nodes")
        sensors = cur.fetchone()

        cur.execute("""
            SELECT ROUND(AVG(decibel_value), 1) AS avg_db, ROUND(MAX(decibel_value), 1) AS peak_db,
                   SUM(violation_flag) AS violations
            FROM noise_readings
            WHERE recorded_at >= CURDATE()
        """)
        today = cur.fetchone()

        cur.execute("SELECT COUNT(*) AS pending FROM alert_logs WHERE status='pending'")
        pending = cur.fetchone()

    return jsonify({
        "sensors_total": sensors["total"] or 0,
        "sensors_active": sensors["active"] or 0,
        "today_avg_db": float(today["avg_db"]) if today["avg_db"] is not None else None,
        "today_peak_db": float(today["peak_db"]) if today["peak_db"] is not None else None,
        "today_violations": today["violations"] or 0,
        "pending_alerts": pending["pending"] or 0,
    })


@bp.get("/violations-by-location")
@login_required
@roles_required("administrator", "system_admin")
def violations_by_location():
    days = request.args.get("days", 7, type=int)
    with db_cursor() as (conn, cur):
        cur.execute(
            f"""SELECT s.location, COUNT(*) AS violation_count
                FROM noise_readings r
                JOIN sensor_nodes s ON s.id = r.sensor_id
                WHERE r.violation_flag = TRUE AND r.recorded_at >= NOW() - INTERVAL {int(days)} DAY
                GROUP BY s.location
                ORDER BY violation_count DESC""",
        )
        rows = cur.fetchall()
    return jsonify({"days": days, "violations_by_location": rows})


@bp.get("/hourly-distribution")
@login_required
@roles_required("administrator", "system_admin")
def hourly_distribution():
    sensor_id = request.args.get("sensor_id", type=int)
    if not sensor_id:
        return jsonify({"error": "sensor_id query parameter is required"}), 400

    with db_cursor() as (conn, cur):
        cur.execute(
            """SELECT HOUR(recorded_at) AS hour_of_day, ROUND(AVG(decibel_value), 1) AS avg_db,
                      ROUND(MAX(decibel_value), 1) AS peak_db
               FROM noise_readings
               WHERE sensor_id=%s AND recorded_at >= NOW() - INTERVAL 7 DAY
               GROUP BY HOUR(recorded_at)
               ORDER BY hour_of_day""",
            (sensor_id,),
        )
        rows = cur.fetchall()
    return jsonify({"sensor_id": sensor_id, "hourly_distribution": rows})
