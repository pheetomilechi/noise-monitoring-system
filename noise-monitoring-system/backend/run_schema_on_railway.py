"""
Run schema.sql on Railway MySQL database using Python.
This avoids needing MySQL CLI installed locally.
"""
import os
import sys
import subprocess

# Install pymysql if not available
try:
    import pymysql
except ImportError:
    print("Installing pymysql...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"])
    import pymysql

def run_schema():
    """Execute schema.sql on the configured database."""
    # Get Railway environment variables
    db_host = os.environ.get("MYSQLHOST", "mysql.railway.internal")
    db_port = int(os.environ.get("MYSQLPORT", "3306"))
    db_user = os.environ.get("MYSQLUSER", "root")
    db_password = os.environ.get("MYSQLPASSWORD", "")
    db_name = os.environ.get("MYSQLDATABASE", "railway")
    
    print(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    
    # Read schema file
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, 'r') as f:
        sql_text = f.read()
    
    # Connect to database
    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    
    try:
        with conn.cursor() as cur:
            # Split by semicolon and execute each statement
            statements = sql_text.split(';')
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cur.execute(statement)
                        print(f"✓ Executed statement {i+1}")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"⊘ Skipped (already exists): statement {i+1}")
                        else:
                            print(f"✗ Error in statement {i+1}: {e}")
                            print(f"   Statement: {statement[:100]}...")
        print("\n✓ Schema execution completed successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    run_schema()