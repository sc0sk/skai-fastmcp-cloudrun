#!/usr/bin/env python3
"""Grant IAM permissions by connecting as postgres user with password."""

import asyncio
import sys
from google.cloud.sql.connector import Connector
import asyncpg


async def grant_iam_permissions():
    """Connect as postgres and grant permissions to IAM service account."""

    # Read postgres password
    with open("/tmp/db_password.txt", "r") as f:
        postgres_password = f.read().strip()

    # Connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db"
    database = "hansard"
    iam_user = "666924716777-compute@developer"

    print(f"🔐 Connecting to Cloud SQL as postgres user...")

    loop = asyncio.get_running_loop()
    async with Connector(loop=loop) as connector:
        conn = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user="postgres",
            password=postgres_password,
            db=database,
        )

        print(f"✅ Connected as postgres")
        print(f"\n🔧 Granting permissions to IAM user: {iam_user}\n")

        # Grant all necessary permissions
        await conn.execute(f'GRANT CONNECT ON DATABASE {database} TO "{iam_user}"')
        print(f"✓ CONNECT on database")

        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{iam_user}"')
        print(f"✓ USAGE on schema")

        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{iam_user}"')
        print(f"✓ SELECT, INSERT, UPDATE, DELETE on all tables")

        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{iam_user}"')
        print(f"✓ USAGE, SELECT on all sequences")

        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{iam_user}"')
        print(f"✓ Default privileges on future tables")

        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{iam_user}"')
        print(f"✓ Default privileges on future sequences")

        print(f"\n✅ All IAM permissions granted successfully!")

        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(grant_iam_permissions())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
