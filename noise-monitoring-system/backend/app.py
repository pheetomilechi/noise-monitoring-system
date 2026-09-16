"""
Real-Time Noise Monitoring System - Backend Entry Point
Faculty of Artificial Intelligence, Taraba State University

Run with:
    python app.py
(after configuring MySQL -- see README.md)
"""
from flask import Flask, jsonify, send_from_directory
import os

from config import Config
from routes import auth, sensors, readings, thresholds, alerts, analytics


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Minimal permissive CORS (frontend is served separately) ---
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Sensor-Key"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_any>", methods=["OPTIONS"])
    def cors_preflight(_any):
        return "", 204

    app.register_blueprint(auth.bp)
    app.register_blueprint(sensors.bp)
    app.register_blueprint(readings.bp)
    app.register_blueprint(thresholds.bp)
    app.register_blueprint(alerts.bp)
    app.register_blueprint(analytics.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "noise-monitoring-backend"})

    # --- Optionally serve the static frontend directly from Flask so the
    # whole system can be run with a single command during grading/demo. ---
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

    @app.get("/")
    def serve_index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/<path:filename>")
    def serve_static(filename):
        if os.path.exists(os.path.join(frontend_dir, filename)):
            return send_from_directory(frontend_dir, filename)
        return jsonify({"error": "Not found"}), 404

    return app


app = create_app()

if __name__ == "__main__":
    # For development only
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
