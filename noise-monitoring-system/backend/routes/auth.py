from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import db_cursor
from utils.auth_utils import issue_token, login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALLOWED_ROLES = {"student", "administrator", "system_admin"}


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "student")
    department = data.get("department")

    if not full_name or not email or not password:
        return jsonify({"error": "full_name, email and password are required"}), 400
    if role not in ALLOWED_ROLES:
        return jsonify({"error": f"role must be one of {sorted(ALLOWED_ROLES)}"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    password_hash = generate_password_hash(password)

    with db_cursor(commit=True) as (conn, cur):
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            return jsonify({"error": "An account with this email already exists"}), 409

        cur.execute(
            """INSERT INTO users (full_name, email, password_hash, role, department)
               VALUES (%s, %s, %s, %s, %s)""",
            (full_name, email, password_hash, role, department),
        )
        user_id = cur.lastrowid

    user = {"id": user_id, "email": email, "role": role, "full_name": full_name}
    token = issue_token(user)
    return jsonify({"token": token, "user": user}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    with db_cursor() as (conn, cur):
        cur.execute(
            "SELECT id, full_name, email, password_hash, role, department FROM users WHERE email=%s",
            (email,),
        )
        user = cur.fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = issue_token(user)
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "department": user["department"],
        },
    })


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": g.current_user})
