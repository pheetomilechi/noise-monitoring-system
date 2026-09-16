"""
JWT issuing/verification and role-based access-control decorators.
"""
import datetime
from functools import wraps

import jwt
from flask import request, jsonify, g

from config import Config


def issue_token(user):
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user["full_name"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_token(token):
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])


def _extract_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def login_required(fn):
    """Attaches the decoded token payload to `g.current_user` on success."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        try:
            g.current_user = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token"}), 401
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*allowed_roles):
    """Stack under @login_required. Returns 403 if the caller's role is
    not in allowed_roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = g.current_user.get("role")
            if role not in allowed_roles:
                return jsonify({"error": "You do not have permission to perform this action"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def sensor_api_key_required(fn):
    """Authenticates ESP8266 sensor nodes via the X-Sensor-Key header
    instead of a user JWT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-Sensor-Key")
        if not api_key:
            return jsonify({"error": "Missing X-Sensor-Key header"}), 401
        g.sensor_api_key = api_key
        return fn(*args, **kwargs)
    return wrapper
