#!/usr/bin/env python3
"""Enable pgvector extension as postgres superuser."""

import asyncio
from google.cloud.sql.connector import Connector
import asyncpg
import os

async def enable_pgvector():
    """Connect as postgres user and enable pgvector extension."""

    # Connection details
    instance_connection_name = "skai-fastmcp-cloudrun:us-central1:hansard-db-v2"
    database = "hansard"
    user = "postgres"
    password = os.getenv("POSTGRES_PASSWORD", "temp-admin-password-123")

    print(f"🔗 Connecting to {instance_connection_name} as {user}...")

    # Initialize connector
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)

    try:
        # Connect using postgres credentials (non-IAM)
        conn = await connector.connect_async(
            instance_connection_name,
            "asyncpg",
            user=user,
            db=database,
            password=password,
            enable_iam_auth=False
        )

        print(f"✅ Connected to database {database}")

        # Enable pgvector extension
        print("🔧 Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ pgvector extension enabled!")

        # Verify extension
        result = await conn.fetchrow(
            "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
        )

        if result:
            print(f"✅ Extension verified: {result['extname']} version {result['extversion']}")
        else:
            print("⚠️  Extension not found after creation")

        # Grant cloudsqlsuperuser role to service account (required for pgvector extension)
        print("\n🔑 Granting cloudsqlsuperuser role to service account...")
        service_account = "666924716777-compute@developer"

        # Grant cloudsqlsuperuser role (allows CREATE EXTENSION)
        await conn.execute(f'GRANT cloudsqlsuperuser TO "{service_account}"')
        print(f"✅ cloudsqlsuperuser role granted to {service_account}")

        # Grant database privileges
        await conn.execute(f'GRANT CONNECT ON DATABASE {database} TO "{service_account}"')
        await conn.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{service_account}"')
        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{service_account}"')
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{service_account}"')

        # Set default privileges
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{service_account}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{service_account}"')

        print(f"✅ Database privileges granted to {service_account}")

        # Close connection
        await conn.close()
        await connector.close_async()

        print("\n" + "="*60)
        print("✅ Database setup complete!")
        print("="*60)
        print(f"📊 Summary:")
        print(f"   - Extension: pgvector {result['extversion'] if result else 'unknown'}")
        print(f"   - Service account: {service_account}")
        print(f"   - Privileges: cloudsqlsuperuser, CONNECT, USAGE, CREATE")
        print("\n🎯 Ready to populate database with IAM authentication!")

    except Exception as e:
        print(f"❌ Error: {e}")
        await connector.close_async()
        raise


if __name__ == "__main__":
    asyncio.run(enable_pgvector())
