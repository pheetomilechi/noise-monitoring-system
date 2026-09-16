"""
Creates the first administrator account. Run once after schema.sql has
been applied:

    python seed_admin.py admin@fai.edu.ng "Faculty Admin" "Admin123!"
"""
import sys

from werkzeug.security import generate_password_hash

from db import db_cursor


def main():
    if len(sys.argv) != 4:
        print('Usage: python seed_admin.py <email> "<full name>" <password>')
        sys.exit(1)

    email, full_name, password = sys.argv[1], sys.argv[2], sys.argv[3]
    password_hash = generate_password_hash(password)

    with db_cursor(commit=True) as (conn, cur):
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            print(f"A user with email {email} already exists.")
            return
        cur.execute(
            """INSERT INTO users (full_name, email, password_hash, role, department)
               VALUES (%s, %s, %s, 'administrator', 'Faculty of Artificial Intelligence')""",
            (full_name, email, password_hash),
        )

    print(f"Administrator account created for {email}.")


if __name__ == "__main__":
    main()
