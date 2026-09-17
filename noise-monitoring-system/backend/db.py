"""
Thin database access layer on top of PyMySQL.

We intentionally avoid a heavy ORM: the project's ERD is small (five
tables) and a query-based layer keeps the SQL visible and easy to
audit -- useful for a project whose write-up documents its schema
explicitly.
"""
import pymysql
import pymysql.cursors
from contextlib import contextmanager

from config import Config


def get_connection():
    """Open a new MySQL connection. Callers are responsible for closing it
    (use the `db_cursor` context manager below instead of calling this
    directly wherever possible)."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def db_cursor(commit=False):
    """Yield a (connection, cursor) pair, closing both automatically and
    rolling back on error. Pass commit=True for INSERT/UPDATE/DELETE."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db_from_schema(schema_path="schema.sql"):
    """Run schema.sql against the configured MySQL server. Useful for
    first-time setup: `python -c "from db import init_db_from_schema; init_db_from_schema()"`
    """
    with open(schema_path, "r") as f:
        sql_text = f.read()

    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            for statement in sql_text.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        cur.execute(statement)
                    except Exception as e:
                        # Skip errors for existing tables/data
                        if "already exists" not in str(e) and "Duplicate entry" not in str(e):
                            raise
    finally:
        conn.close()
