#!/usr/bin/env python3
"""Grant IAM permissions to scott.coleman@aph.gov.au user."""

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from google.cloud.sql.connector import Connector
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
REGION = os.getenv("GCP_REGION", "us-central1")
INSTANCE = os.getenv("CLOUDSQL_INSTANCE", "hansard-db")
DATABASE = os.getenv("CLOUDSQL_DATABASE", "hansard")


async def grant_permissions():
    """Grant IAM user permissions."""
    print("🔐 Granting IAM Permissions")
    print("=" * 50)

    connector = None

    try:
        loop = asyncio.get_running_loop()
        connector = Connector(loop=loop)

        # Connect as postgres user
        conn = await connector.connect_async(
            f"{PROJECT_ID}:{REGION}:{INSTANCE}",
            "asyncpg",
            user="postgres",
            password="temp-admin-password-123",
            db=DATABASE,
            enable_iam_auth=False,
        )

        print("✅ Connected as postgres")

        # Grant permissions to IAM user
        iam_user = "scott.coleman@aph.gov.au"

        print(f"\n🎫 Granting permissions to {iam_user}...")

        await conn.execute(f'GRANT CONNECT ON DATABASE {DATABASE} TO "{iam_user}"')
        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{iam_user}"')
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{iam_user}"')
        await conn.execute(
            f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{iam_user}"'
        )

        # Grant future privileges
        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "{iam_user}"'
        )
        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "{iam_user}"'
        )

        print(f"✅ Permissions granted to {iam_user}")

        # Verify
        print("\n🔍 Verifying permissions...")
        result = await conn.fetch("""
            SELECT
                grantee,
                privilege_type
            FROM information_schema.table_privileges
            WHERE grantee = $1 AND table_name IN ('speeches', 'speech_chunks')
            ORDER BY table_name, privilege_type
        """, iam_user)

        print(f"\nTable privileges for {iam_user}:")
        for row in result:
            print(f"  - {row['privilege_type']}")

        await conn.close()
        if connector:
            await connector.close_async()

        print("\n✅ IAM permissions setup complete!")
        print("\nNext steps:")
        print("1. Remove postgres password (security best practice):")
        print("   gcloud sql users set-password postgres --instance=hansard-db --prompt-for-password")
        print("2. Update scripts to use IAM auth")
        print("3. Run ingestion with IAM auth")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        if connector:
            await connector.close_async()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(grant_permissions())
    sys.exit(exit_code)
