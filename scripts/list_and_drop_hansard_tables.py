#!/usr/bin/env python3
"""List all tables and drop any hansard-related tables."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine


async def main():
    """List and drop hansard tables."""
    print("=" * 80)
    print("List and Drop Hansard Tables")
    print("=" * 80)

    # Connect
    print("\n🔌 Connecting to Cloud SQL...")
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    # Use the sync engine connection
    print("\n📋 Listing all tables...")

    async def list_tables():
        """List all tables using raw SQL."""
        from sqlalchemy import text
        async with engine._engine.begin() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = [row[0] for row in result]
            return tables

    tables = await list_tables()

    print(f"\n   Found {len(tables)} tables:")
    for table in tables:
        print(f"   - {table}")

    # Find hansard-related tables
    hansard_tables = [t for t in tables if 'hansard' in t.lower() or 'speech' in t.lower()]

    if not hansard_tables:
        print("\n   ✅ No hansard-related tables found")
    else:
        print(f"\n🗑️  Found {len(hansard_tables)} hansard-related tables to drop:")
        for table in hansard_tables:
            print(f"   - {table}")

        # Drop each table
        async def drop_tables():
            from sqlalchemy import text
            async with engine._engine.begin() as conn:
                for table in hansard_tables:
                    print(f"\n   Dropping {table}...")
                    await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    print(f"   ✅ Dropped {table}")

        await drop_tables()
        print("\n✅ All hansard tables dropped")

    # Close
    await engine.close()
    print("\n🔌 Connection closed\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
