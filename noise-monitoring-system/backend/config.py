"""
Configuration for the Real-Time Noise Monitoring System backend.
All values can be overridden with environment variables so the same
code runs unchanged in development, testing, and production.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    # --- MySQL connection ---
    DB_HOST = os.environ.get("NMS_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("NMS_DB_PORT", "3306"))
    DB_USER = os.environ.get("NMS_DB_USER", "root")
    DB_PASSWORD = os.environ.get("NMS_DB_PASSWORD", "")
    DB_NAME = os.environ.get("NMS_DB_NAME", "noise_monitoring")

    # --- Auth ---
    JWT_SECRET = os.environ.get("NMS_JWT_SECRET", "change-this-secret-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = int(os.environ.get("NMS_JWT_EXPIRY_HOURS", "12"))

    # --- App ---
    DEBUG = os.environ.get("NMS_DEBUG", "true").lower() == "true"
    HOST = os.environ.get("NMS_HOST", "0.0.0.0")
    PORT = int(os.environ.get("NMS_PORT", "5000"))

    # --- Notifications (optional; disabled unless SMTP vars are set) ---
    SMTP_HOST = os.environ.get("NMS_SMTP_HOST")
    SMTP_PORT = int(os.environ.get("NMS_SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("NMS_SMTP_USER")
    SMTP_PASSWORD = os.environ.get("NMS_SMTP_PASSWORD")
    SMTP_FROM = os.environ.get("NMS_SMTP_FROM", "noise-monitor@fai.edu.ng")
