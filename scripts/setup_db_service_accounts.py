#!/usr/bin/env python3
"""Setup database service accounts with proper permissions.

This script:
1. Connects as the admin service account (hansard-db-admin)
2. Creates database users for both service accounts
3. Grants appropriate permissions:
   - hansard-db-admin: Full ownership (CREATE, DROP, ALTER tables)
   - hansard-db-readonly: Read-only (SELECT only)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
from google.cloud.sql.connector import Connector


async def setup_service_accounts():
    """Set up database service accounts with appropriate permissions."""

    project_id = os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    region = os.getenv("GCP_REGION", "us-central1")
    instance = os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2")
    database = os.getenv("CLOUDSQL_DATABASE", "hansard")

    admin_user = "hansard-db-admin@skai-fastmcp-cloudrun.iam"
    readonly_user = "hansard-db-readonly@skai-fastmcp-cloudrun.iam"

    print(f"🔌 Connecting to Cloud SQL as admin...")
    print(f"   Project: {project_id}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}")

    # Initialize Cloud SQL Python Connector
    connector = Connector()

    async def getconn() -> asyncpg.Connection:
        conn = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user=admin_user,
            db=database,
            enable_iam_auth=True,
        )
        return conn

    conn = await getconn()

    try:
        print(f"\n👤 Setting up database users...")

        # Create admin user if not exists
        await conn.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{admin_user}') THEN
                    CREATE USER "{admin_user}";
                END IF;
            END
            $$;
        """)
        print(f"   ✅ Admin user: {admin_user}")

        # Create readonly user if not exists
        await conn.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{readonly_user}') THEN
                    CREATE USER "{readonly_user}";
                END IF;
            END
            $$;
        """)
        print(f"   ✅ Readonly user: {readonly_user}")

        print(f"\n🔐 Granting permissions...")

        # Grant admin full database permissions
        await conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE {database} TO "{admin_user}";')
        await conn.execute(f'GRANT ALL PRIVILEGES ON SCHEMA public TO "{admin_user}";')
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{admin_user}";')
        await conn.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{admin_user}";')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{admin_user}";')
        print(f"   ✅ Admin: Full database access")

        # Grant readonly SELECT only
        await conn.execute(f'GRANT CONNECT ON DATABASE {database} TO "{readonly_user}";')
        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{readonly_user}";')
        await conn.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{readonly_user}";')
        await conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "{readonly_user}";')
        print(f"   ✅ Readonly: SELECT only")

        # Make sure hansard_speeches table is owned by admin (if it exists)
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        if any(row['tablename'] == 'hansard_speeches' for row in tables):
            await conn.execute(f'ALTER TABLE hansard_speeches OWNER TO "{admin_user}";')
            print(f"   ✅ Transferred hansard_speeches ownership to admin")

        print(f"\n✅ Database service accounts configured successfully!")
        print(f"\nAccount Summary:")
        print(f"   📝 Admin: {admin_user}")
        print(f"      - Can CREATE/DROP/ALTER tables")
        print(f"      - Owns hansard_speeches table")
        print(f"      - Use for schema migrations")
        print(f"\n   👁️  Readonly: {readonly_user}")
        print(f"      - Can SELECT from tables only")
        print(f"      - Use for MCP server queries")

    finally:
        await conn.close()
        await connector.close_async()
        print(f"\n🔌 Closed database connection")


if __name__ == "__main__":
    try:
        asyncio.run(setup_service_accounts())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
