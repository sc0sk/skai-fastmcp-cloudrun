#!/usr/bin/env python3
"""Test IAM authentication to Cloud SQL.

Verifies that IAM auth works for database connection.
"""

import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from storage.cloud_sql_engine import CloudSQLEngine


def test_iam_connection():
    """Test IAM-based database connection."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          Testing Cloud SQL IAM Authentication                 ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    try:
        print("1. Creating Cloud SQL engine with IAM auth...")
        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard_db_fresh",
            user=None,  # Triggers IAM auth
            password=None,
        )
        print("   ✓ Engine created")

        print("\n2. Testing database connection...")
        with engine_mgr.engine.connect() as conn:
            print("   ✓ Connected successfully")

            # Test query
            print("\n3. Running test query...")
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✓ PostgreSQL version: {version[:50]}...")

            print("\n4. Checking database...")
            query = "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"
            result = conn.execute(text(query))
            table_count = result.scalar()
            print(f"   ✓ Found {table_count} tables in public schema")

        engine_mgr.close()

        print("\n" + "=" * 66)
        print("  ✅ IAM AUTHENTICATION TEST PASSED")
        print("=" * 66)
        print("\nResults:")
        print("  ✓ Service account detected and used")
        print("  ✓ Cloud SQL Connector IAM auth working")
        print("  ✓ Database connection established")
        print("  ✓ Queries executing successfully")
        print("\nThe database is ready for Feature 017 population!")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_iam_connection()
    sys.exit(0 if success else 1)
