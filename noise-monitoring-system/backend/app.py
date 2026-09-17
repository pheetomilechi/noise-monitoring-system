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
        try:
            from db import get_connection
            from config import Config
            conn = get_connection()
            conn.close()
            return jsonify({
                "status": "ok", 
                "service": "noise-monitoring-backend", 
                "database": "connected",
                "db_config": {
                    "host": Config.DB_HOST,
                    "port": Config.DB_PORT,
                    "database": Config.DB_NAME,
                    "user": Config.DB_USER
                }
            })
        except Exception as e:
            return jsonify({
                "status": "error", 
                "service": "noise-monitoring-backend", 
                "database": "disconnected", 
                "error": str(e),
                "db_config": {
                    "host": Config.DB_HOST,
                    "port": Config.DB_PORT,
                    "database": Config.DB_NAME,
                    "user": Config.DB_USER
                }
            }), 500

    @app.route("/api/setup/database", methods=["GET", "POST"])
    def setup_database():
        """One-time endpoint to run schema.sql on the database."""
        try:
            from db import get_connection
            import os
            
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, 'r') as f:
                sql_text = f.read()
            
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    statements = sql_text.split(';')
                    results = []
                    for i, statement in enumerate(statements):
                        statement = statement.strip()
                        if statement and not statement.startswith('--'):
                            try:
                                cur.execute(statement)
                                results.append(f"Statement {i+1}: Success")
                            except Exception as e:
                                if "already exists" in str(e):
                                    results.append(f"Statement {i+1}: Skipped (already exists)")
                                else:
                                    results.append(f"Statement {i+1}: Error - {str(e)}")
                    conn.commit()
                return jsonify({"status": "success", "results": results})
            finally:
                conn.close()
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    # --- Optionally serve the static frontend directly from Flask so the
    # whole system can be run with a single command during grading/demo. ---
    # Try multiple possible frontend locations for flexibility
    possible_frontend_dirs = [
        os.path.join(os.path.dirname(__file__), "frontend"),  # Inside backend directory (Railway)
        os.path.join(os.path.dirname(__file__), "..", "frontend"),  # Standard structure
        "/app/frontend",  # Docker container
        "frontend",  # Relative path
        "/workspace/frontend",  # Railway workspace
    ]
    
    frontend_dir = None
    for dir_path in possible_frontend_dirs:
        if os.path.exists(dir_path) and os.path.exists(os.path.join(dir_path, "index.html")):
            frontend_dir = dir_path
            break
    
    if frontend_dir:
        @app.get("/")
        def serve_index():
            return send_from_directory(frontend_dir, "index.html")

        @app.get("/<path:filename>")
        def serve_static(filename):
            if os.path.exists(os.path.join(frontend_dir, filename)):
                return send_from_directory(frontend_dir, filename)
            return jsonify({"error": "Not found"}), 404
    else:
        # If frontend not found, provide API info and debug info
        @app.get("/")
        def serve_root():
            return jsonify({
                "message": "Noise Monitoring System API",
                "api_health": "/api/health",
                "frontend_not_found": "Frontend files not found - serving API only",
                "debug": {
                    "current_dir": os.getcwd(),
                    "script_dir": os.path.dirname(__file__),
                    "searched_paths": possible_frontend_dirs,
                    "path_exists": [os.path.exists(p) for p in possible_frontend_dirs],
                    "root_contents": os.listdir("/") if os.path.exists("/") else [],
                    "app_contents": os.listdir("/app") if os.path.exists("/app") else []
                }
            })

    return app


app = create_app()

if __name__ == "__main__":
    # For development only
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
