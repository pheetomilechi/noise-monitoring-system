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
            
            # Define table creation statements in order
            table_statements = [
                """CREATE TABLE IF NOT EXISTS users (
                  id              INT AUTO_INCREMENT PRIMARY KEY,
                  full_name       VARCHAR(150) NOT NULL,
                  email           VARCHAR(150) NOT NULL UNIQUE,
                  password_hash   VARCHAR(255) NOT NULL,
                  role            ENUM('student', 'administrator', 'system_admin') NOT NULL DEFAULT 'student',
                  department      VARCHAR(150) DEFAULT NULL,
                  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB""",
                
                """CREATE TABLE IF NOT EXISTS sensor_nodes (
                  id                  INT AUTO_INCREMENT PRIMARY KEY,
                  sensor_code         VARCHAR(50) NOT NULL UNIQUE,
                  api_key             VARCHAR(64) NOT NULL UNIQUE,
                  location            VARCHAR(150) NOT NULL,
                  room_identifier     VARCHAR(100) NOT NULL,
                  calibration_offset  DECIMAL(5,2) NOT NULL DEFAULT 0.00,
                  status              ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
                  last_seen           TIMESTAMP NULL DEFAULT NULL,
                  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB""",
                
                """CREATE TABLE IF NOT EXISTS noise_readings (
                  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
                  sensor_id       INT NOT NULL,
                  decibel_value   DECIMAL(5,2) NOT NULL,
                  recorded_at     DATETIME NOT NULL,
                  violation_flag  BOOLEAN NOT NULL DEFAULT FALSE,
                  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  CONSTRAINT fk_reading_sensor FOREIGN KEY (sensor_id)
                    REFERENCES sensor_nodes(id) ON DELETE CASCADE,
                  INDEX idx_sensor_time (sensor_id, recorded_at)
                ) ENGINE=InnoDB""",
                
                """CREATE TABLE IF NOT EXISTS alert_thresholds (
                  id                       INT AUTO_INCREMENT PRIMARY KEY,
                  sensor_id                INT NOT NULL,
                  label                    VARCHAR(100) DEFAULT 'Default',
                  max_decibel              DECIMAL(5,2) NOT NULL,
                  hysteresis_db            DECIMAL(4,2) NOT NULL DEFAULT 3.00,
                  period_start             TIME NOT NULL DEFAULT '00:00:00',
                  period_end               TIME NOT NULL DEFAULT '23:59:59',
                  notification_recipients  JSON DEFAULT NULL,
                  is_active                BOOLEAN NOT NULL DEFAULT TRUE,
                  created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  CONSTRAINT fk_threshold_sensor FOREIGN KEY (sensor_id)
                    REFERENCES sensor_nodes(id) ON DELETE CASCADE
                ) ENGINE=InnoDB""",
                
                """CREATE TABLE IF NOT EXISTS alert_logs (
                  id              INT AUTO_INCREMENT PRIMARY KEY,
                  threshold_id    INT NOT NULL,
                  sensor_id       INT NOT NULL,
                  reading_id      BIGINT DEFAULT NULL,
                  decibel_value   DECIMAL(5,2) NOT NULL,
                  user_id         INT DEFAULT NULL,
                  triggered_at    DATETIME NOT NULL,
                  acknowledged_at DATETIME DEFAULT NULL,
                  status          ENUM('pending', 'acknowledged') NOT NULL DEFAULT 'pending',
                  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  CONSTRAINT fk_alert_threshold FOREIGN KEY (threshold_id)
                    REFERENCES alert_thresholds(id) ON DELETE CASCADE,
                  CONSTRAINT fk_alert_sensor FOREIGN KEY (sensor_id)
                    REFERENCES sensor_nodes(id) ON DELETE CASCADE,
                  CONSTRAINT fk_alert_user FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB"""
            ]
            
            # Define seed data statements
            seed_statements = [
                """INSERT IGNORE INTO sensor_nodes (sensor_code, api_key, location, room_identifier, calibration_offset, status)
                VALUES
                  ('SN-LR-01', 'demo-key-lr01-change-me', 'Lecture Room 1, FAI Building', 'LR-01', 2.5, 'active'),
                  ('SN-LAB-02', 'demo-key-lab02-change-me', 'AI Computer Lab, FAI Building', 'LAB-02', 1.0, 'active'),
                  ('SN-LIB-03', 'demo-key-lib03-change-me', 'Silent Study Area, FAI Library', 'LIB-03', 0.5, 'active')""",
                
                """INSERT IGNORE INTO alert_thresholds (sensor_id, label, max_decibel, hysteresis_db, period_start, period_end)
                SELECT id, 'Lecture hours limit', 65.00, 3.00, '08:00:00', '18:00:00' FROM sensor_nodes WHERE sensor_code = 'SN-LR-01'""",
                
                """INSERT IGNORE INTO alert_thresholds (sensor_id, label, max_decibel, hysteresis_db, period_start, period_end)
                SELECT id, 'Lab session limit', 60.00, 3.00, '08:00:00', '20:00:00' FROM sensor_nodes WHERE sensor_code = 'SN-LAB-02'""",
                
                """INSERT IGNORE INTO alert_thresholds (sensor_id, label, max_decibel, hysteresis_db, period_start, period_end)
                SELECT id, 'Silent area limit', 45.00, 2.00, '00:00:00', '23:59:59' FROM sensor_nodes WHERE sensor_code = 'SN-LIB-03'"""
            ]
            
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    results = []
                    
                    # Create tables first
                    for i, statement in enumerate(table_statements):
                        try:
                            cur.execute(statement)
                            conn.commit()
                            results.append(f"Table {i+1}: Success")
                        except Exception as e:
                            if "already exists" in str(e):
                                results.append(f"Table {i+1}: Skipped (already exists)")
                            else:
                                results.append(f"Table {i+1}: Error - {str(e)}")
                    
                    # Then insert seed data
                    for i, statement in enumerate(seed_statements):
                        try:
                            cur.execute(statement)
                            conn.commit()
                            results.append(f"Seed {i+1}: Success")
                        except Exception as e:
                            if "Duplicate entry" in str(e):
                                results.append(f"Seed {i+1}: Skipped (duplicate)")
                            else:
                                results.append(f"Seed {i+1}: Error - {str(e)}")
                
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
