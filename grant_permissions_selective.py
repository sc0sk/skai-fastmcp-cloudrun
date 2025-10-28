#!/usr/bin/env python3
"""Grant IAM service account permissions on tables that postgres owns."""

import asyncio
from google.cloud.sql.connector import Connector
import asyncpg
import os

async def grant_permissions():
    """Connect as postgres and grant permissions selectively."""

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

        service_account = "666924716777-compute@developer"

        # List all tables and their owners
        print("\n📋 Listing tables and owners...")
        tables = await conn.fetch("""
            SELECT schemaname, tablename, tableowner 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        for row in tables:
            print(f"  - {row['tablename']} (owner: {row['tableowner']})")

        # Grant schema-level privileges
        print(f"\n🔑 Granting schema privileges to {service_account}...")
        await conn.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{service_account}"')
        print(f"✅ Schema privileges granted")

        # Grant privileges on tables owned by postgres
        print(f"\n🔑 Granting table privileges...")
        postgres_tables = [row['tablename'] for row in tables if row['tableowner'] == 'postgres']
        
        if postgres_tables:
            for table in postgres_tables:
                try:
                    await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO "{service_account}"')
                    print(f"  ✅ Granted permissions on {table}")
                except Exception as e:
                    print(f"  ⚠️  Failed to grant on {table}: {e}")
        else:
            print("  ⚠️  No tables owned by postgres")

        # Grant privileges on sequences
        print(f"\n🔑 Granting sequence privileges...")
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{service_account}"')
        print(f"✅ Sequence privileges granted")

        # Set default privileges for future tables
        print(f"\n🔑 Setting default privileges...")
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{service_account}"')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{service_account}"')
        print(f"✅ Default privileges set")

        # For tables not owned by postgres, show manual steps
        other_tables = [row for row in tables if row['tableowner'] != 'postgres']
        if other_tables:
            print(f"\n⚠️  Manual action required for tables not owned by postgres:")
            for row in other_tables:
                print(f"\n  Table: {row['tablename']} (owner: {row['tableowner']})")
                print(f"  Run as {row['tableowner']} or as a superuser:")
                print(f'  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{row["tablename"]}" TO "{service_account}";')

        # Close connection
        await conn.close()
        await connector.close_async()

        print("\n" + "="*60)
        print("✅ Permission grant complete!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        await connector.close_async()
        raise


if __name__ == "__main__":
    asyncio.run(grant_permissions())
