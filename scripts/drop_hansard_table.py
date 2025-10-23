#!/usr/bin/env python3
"""Drop hansard_speeches table to allow LangChain to recreate with correct schema."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine


async def main():
    """Drop hansard_speeches table."""
    print("=" * 80)
    print("Drop Hansard Speeches Table")
    print("=" * 80)

    # Connect
    print("\n🔌 Connecting to Cloud SQL...")
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    # Drop table
    print("\n🗑️  Dropping hansard_speeches table (CASCADE)...")
    async with engine._pool.connect() as conn:
        await conn.execute("DROP TABLE IF EXISTS hansard_speeches CASCADE")
        print("   ✅ Table dropped")

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