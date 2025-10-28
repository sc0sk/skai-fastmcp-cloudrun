#!/usr/bin/env python3
"""Grant permissions to the IAM user scott.coleman@aph.gov.au."""

import asyncio
from google.cloud.sql.connector import Connector
import os

async def grant():
    """Connect as postgres and grant permissions to IAM user."""

    instance_conn = "skai-fastmcp-cloudrun:us-central1:hansard-db-v2"
    database = "hansard"
    user = "postgres"
    password = os.getenv("POSTGRES_PASSWORD", "temp-admin-password-123")

    print(f"🔗 Connecting to {instance_conn} as {user}...")

    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)

    try:
        conn = await connector.connect_async(
            instance_conn,
            "asyncpg",
            user=user,
            db=database,
            password=password,
            enable_iam_auth=False
        )

        print(f"✅ Connected to database {database}")

        iam_user = "scott.coleman@aph.gov.au"

        print(f"\n🔑 Granting permissions to {iam_user}...")

        # Grant schema privileges
        await conn.execute(
            f'GRANT USAGE, CREATE ON SCHEMA public TO "{iam_user}"'
        )
        print(f"  ✅ Schema privileges")

        # Grant table privileges
        await conn.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE speeches '
            f'TO "{iam_user}"'
        )
        print(f"  ✅ speeches table")

        # Grant sequence privileges
        await conn.execute(
            f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public '
            f'TO "{iam_user}"'
        )
        print(f"  ✅ Sequences")

        # Default privileges
        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{iam_user}"'
        )
        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
            f'GRANT USAGE, SELECT ON SEQUENCES TO "{iam_user}"'
        )
        print(f"  ✅ Default privileges")

        await conn.close()
        await connector.close_async()

        print("\n✅ Permissions granted successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        await connector.close_async()
        raise


if __name__ == "__main__":
    asyncio.run(grant())
