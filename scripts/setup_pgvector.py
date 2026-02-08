"""
SAP Transformation Management Platform
pgvector extension setup for PostgreSQL.

Usage:
    python scripts/setup_pgvector.py

Requires running PostgreSQL with pgvector image (pgvector/pgvector:pg16).
"""

import os
import sys

try:
    import psycopg
except ImportError:
    print("psycopg not installed. Run: pip install 'psycopg[binary]'")
    sys.exit(1)


def setup_pgvector():
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://sap_user:sap_pass@localhost:5432/sap_platform_dev",
    )

    # Parse simple PostgreSQL URL
    # Format: postgresql://user:pass@host:port/dbname
    parts = db_url.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")

    conn_params = {
        "user": user_pass[0],
        "password": user_pass[1],
        "host": host_port[0],
        "port": int(host_port[1]) if len(host_port) > 1 else 5432,
        "dbname": host_db[1],
    }

    print(f"Connecting to {conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}...")

    with psycopg.connect(**conn_params) as conn:
        conn.autocommit = True

        # Create pgvector extension
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✅ pgvector extension created/confirmed")

        # Create test database if not exists
        test_db = os.getenv("TEST_DATABASE_URL", "").split("/")[-1] or "sap_platform_test"
        try:
            conn.execute(f"CREATE DATABASE {test_db};")
            print(f"✅ Test database '{test_db}' created")
        except Exception:
            print(f"ℹ️  Test database '{test_db}' already exists")

        # Enable pgvector on test DB too
        test_conn_params = {**conn_params, "dbname": test_db}
        try:
            with psycopg.connect(**test_conn_params) as test_conn:
                test_conn.autocommit = True
                test_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print(f"✅ pgvector extension enabled on '{test_db}'")
        except Exception as e:
            print(f"⚠️  Could not enable pgvector on test DB: {e}")

    print("\n✅ pgvector setup complete!")


if __name__ == "__main__":
    setup_pgvector()
