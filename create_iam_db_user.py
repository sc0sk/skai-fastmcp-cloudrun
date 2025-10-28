#!/usr/bin/env python3
"""Create IAM-based database user for Cloud SQL."""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from cloud_sql_python_connector import Connector

# Configuration
PROJECT_ID = "skai-fastmcp-cloudrun"
REGION = "us-central1"
INSTANCE = "hansard-db-v2"
DATABASE = "hansard_db_fresh"
IAM_SA = "hansard-cloud-sql-iam@skai-fastmcp-cloudrun.iam.gserviceaccount.com"


def create_iam_user():
    """Create IAM-based database user."""

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     Creating IAM-Based Database User                         ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    connector = None
    try:
        # Create engine using Cloud SQL Connector
        print("1. Connecting to PostgreSQL via Cloud SQL Connector...")

        # Initialize connector
        connector = Connector()

        def getconn():
            return connector.connect(
                f"{PROJECT_ID}:{REGION}:{INSTANCE}",
                "pg8000",
                user="postgres",
                db=DATABASE,
                enable_iam_auth=True,
            )

        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )

        with engine.begin() as conn:
            print("   ✓ Connected successfully")

            # Create IAM user
            print(f"\n2. Creating IAM user: {IAM_SA}...")
            try:
                conn.execute(text(f'CREATE USER "{IAM_SA}" WITH LOGIN'))
                print("   ✓ User created")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    print("   ✓ User already exists")
                else:
                    raise

            # Grant permissions
            print(f"\n3. Granting permissions to {IAM_SA}...")

            conn.execute(
                text(f'GRANT CONNECT ON DATABASE {DATABASE} '
                     f'TO "{IAM_SA}"')
            )
            print("   ✓ GRANT CONNECT")

            conn.execute(
                text(f'GRANT USAGE ON SCHEMA public TO "{IAM_SA}"')
            )
            print("   ✓ GRANT USAGE ON SCHEMA")

            conn.execute(
                text(f'GRANT ALL PRIVILEGES ON ALL TABLES '
                     f'IN SCHEMA public TO "{IAM_SA}"')
            )
            print("   ✓ GRANT ALL ON TABLES")

            conn.execute(
                text(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES '
                     f'IN SCHEMA public TO "{IAM_SA}"')
            )
            print("   ✓ GRANT ALL ON SEQUENCES")

            conn.execute(
                text(f'GRANT ALL PRIVILEGES ON ALL FUNCTIONS '
                     f'IN SCHEMA public TO "{IAM_SA}"')
            )
            print("   ✓ GRANT ALL ON FUNCTIONS")

            # Set default privileges for future objects
            conn.execute(
                text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                     f'GRANT ALL ON TABLES TO "{IAM_SA}"')
            )
            print("   ✓ ALTER DEFAULT PRIVILEGES ON TABLES")

            conn.execute(
                text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                     f'GRANT ALL ON SEQUENCES TO "{IAM_SA}"')
            )
            print("   ✓ ALTER DEFAULT PRIVILEGES ON SEQUENCES")

            # Verify
            print("\n4. Verifying user permissions...")
            result = conn.execute(
                text(f"SELECT * FROM "
                     f"information_schema.role_table_grants "
                     f"WHERE grantee = '{IAM_SA}' LIMIT 5")
            )
            rows = result.fetchall()
            print(f"   ✓ User has {len(rows)} table grants")

            print("\n" + "=" * 66)
            print("  SETUP COMPLETE")
            print("=" * 66)
            print(f"\nIAM Service Account User Created: {IAM_SA}")
            print("\nNext steps:")
            print("  1. Set environment variables in Cloud Run:")
            print(f"     CLOUD_SQL_USER={IAM_SA}")
            print("     CLOUD_SQL_ENABLE_IAM_AUTH=true")
            print("  2. Update cloud_sql_engine.py if needed")
            print("  3. Redeploy Cloud Run service")
            print("  4. Test database connection")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if connector is not None:
            connector.close()

    return True


if __name__ == "__main__":
    success = create_iam_user()
    sys.exit(0 if success else 1)
