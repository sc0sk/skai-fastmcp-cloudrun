#!/usr/bin/env python3
"""Grant database permissions to Cloud Run service account for IAM authentication."""

import asyncio
import sys
from google.cloud.sql.connector import Connector
import asyncpg


async def grant_permissions():
    """Grant database permissions to IAM service account."""

    # Connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db"
    database = "hansard"
    iam_service_account = "666924716777-compute@developer"

    # Initialize connector
    loop = asyncio.get_running_loop()
    async with Connector(loop=loop) as connector:
        # Connect as IAM user (scott.coleman@aph.gov.au) to grant permissions
        print(f"🔐 Connecting to Cloud SQL as IAM user...")

        conn = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user="scott.coleman@aph.gov.au",
            db=database,
            enable_iam_auth=True,
        )

        print(f"✅ Connected successfully")
        print(f"\n🔧 Granting permissions to: {iam_service_account}\n")

        # Grant database connection
        await conn.execute(f'GRANT CONNECT ON DATABASE {database} TO "{iam_service_account}"')
        print(f"✓ Granted CONNECT on database")

        # Grant schema usage
        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{iam_service_account}"')
        print(f"✓ Granted USAGE on schema public")

        # Grant table permissions
        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{iam_service_account}"')
        print(f"✓ Granted SELECT, INSERT, UPDATE, DELETE on all tables")

        # Grant sequence permissions
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{iam_service_account}"')
        print(f"✓ Granted USAGE, SELECT on all sequences")

        # Grant default privileges for future objects
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{iam_service_account}"')
        print(f"✓ Granted default privileges on future tables")

        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{iam_service_account}"')
        print(f"✓ Granted default privileges on future sequences")

        print(f"\n✅ All permissions granted successfully!")

        # Verify by checking table permissions
        result = await conn.fetch("""
            SELECT grantee, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = $1 AND table_schema = 'public'
            LIMIT 10
        """, iam_service_account)

        if result:
            print(f"\n📋 Verified permissions for {iam_service_account}:")
            for row in result:
                print(f"   - {row['privilege_type']}")

        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(grant_permissions())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
