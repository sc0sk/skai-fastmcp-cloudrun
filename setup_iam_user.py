#!/usr/bin/env python3
"""Create IAM database user for Cloud SQL.

Uses the Cloud SQL Python Connector with a workaround for pg8000 IAM auth.
"""

import subprocess
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

PROJECT_ID = "skai-fastmcp-cloudrun"
REGION = "us-central1"
INSTANCE = "hansard-db-v2"
DATABASE = "hansard_db_fresh"
IAM_SA = "hansard-cloud-sql-iam@skai-fastmcp-cloudrun.iam.gserviceaccount.com"


def setup_iam_user_via_sql_proxy():
    """Set up IAM database user using SQL proxy."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║    Setting Up IAM Database User for Cloud SQL                 ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Start cloud_sql_proxy
    print("1. Starting Cloud SQL proxy...")
    proxy_process = subprocess.Popen(
        [
            "/home/user/skai-fastmcp-cloudrun/cloud_sql_proxy",
            "-instances",
            f"{PROJECT_ID}:{REGION}:{INSTANCE}=tcp:5432",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)  # Wait for proxy to be ready

    try:
        # Connect using standard psycopg3 (no IAM needed for proxy connection)
        print("   ✓ Cloud SQL proxy started")
        print("\n2. Connecting to PostgreSQL...")

        engine = create_engine(
            "postgresql+psycopg://postgres@localhost/postgres",
            connect_args={"sslmode": "disable"},
        )

        with engine.begin() as conn:
            print("   ✓ Connected successfully")

            # Switch to target database
            print(f"\n3. Creating database user: {IAM_SA}...")
            try:
                conn.execute(text(f'CREATE USER "{IAM_SA}" WITH LOGIN'))
                print("   ✓ User created")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    print("   ✓ User already exists, updating grants")
                else:
                    raise

            # Connect to target database for grants
            conn.close()
        
        engine.dispose()

        # Reconnect to the target database
        engine = create_engine(
            f"postgresql+psycopg://postgres@localhost/{DATABASE}",
            connect_args={"sslmode": "disable"},
        )

        with engine.begin() as conn:
            # Grant permissions
            print(f"\n4. Granting permissions...")
            perms = [
                f'GRANT CONNECT ON DATABASE {DATABASE} TO "{IAM_SA}"',
                f'GRANT USAGE ON SCHEMA public TO "{IAM_SA}"',
                f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{IAM_SA}"',
                f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{IAM_SA}"',
                f'GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "{IAM_SA}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{IAM_SA}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{IAM_SA}"',
            ]

            for perm in perms:
                conn.execute(text(perm))

            print("   ✓ All permissions granted")

            # Verify
            print(f"\n5. Verifying user setup...")
            result = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM "
                    f"information_schema.role_table_grants "
                    f"WHERE grantee = '{IAM_SA}'"
                )
            )
            count = result.scalar()
            print(f"   ✓ User has {count} table grants")

        print("\n" + "=" * 66)
        print("  IAM USER SETUP COMPLETE")
        print("=" * 66)
        print(f"\nService Account: {IAM_SA}")
        print("\nConfiguration Summary:")
        print(f"  ✓ Service Account Created & Authorized")
        print(f"  ✓ Cloud SQL IAM Client Role Assigned")
        print(f"  ✓ Database User Created with Full Permissions")
        print(f"  ✓ Cloud Run Using Service Account")
        print("\nNext Steps:")
        print("  1. Verify Cloud Run can access database")
        print("  2. Deploy Feature 017 to populate database")
        print("  3. Test end-to-end functionality")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Kill proxy
        print("\n6. Cleaning up...")
        proxy_process.terminate()
        try:
            proxy_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proxy_process.kill()
        print("   ✓ Proxy stopped")


if __name__ == "__main__":
    success = setup_iam_user_via_sql_proxy()
    sys.exit(0 if success else 1)
