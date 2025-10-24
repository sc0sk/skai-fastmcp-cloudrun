#!/usr/bin/env python3
"""Drop and recreate hansard_speeches table with correct LangChain schema.

This script connects using IAM authentication and manually drops/recreates the table.
Run this if you need to fix schema issues.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine
from sqlalchemy import Column, String, Date, Text


async def drop_and_recreate():
    """Drop hansard_speeches and recreate with correct schema."""
    print("🔌 Connecting to Cloud SQL...")

    # Connect without specifying user to use default IAM auth
    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    print("🗑️  Attempting to drop hansard_speeches table...")

    # Try to drop table manually using raw SQL
    try:
        async with engine._engine.begin() as conn:
            await conn.execute("DROP TABLE IF EXISTS hansard_speeches CASCADE")
        print("✅ Table dropped successfully")
    except Exception as e:
        print(f"⚠️  Could not drop table: {e}")
        print("Continuing anyway - will try to create...")

    print("📊 Creating hansard_speeches table with LangChain schema...")

    # Define custom metadata columns for frequently-filtered fields
    metadata_columns = [
        Column("speaker", String(200)),
        Column("party", String(100)),
        Column("chamber", String(50)),
        Column("date", Date),
        Column("speech_type", String(100)),
        Column("electorate", String(100)),
        Column("speaker_id", String(20)),
        Column("utterance_id", String(100)),
        Column("debate", Text),
    ]

    # Create table with overwrite_existing=True
    await engine.ainit_vectorstore_table(
        table_name="hansard_speeches",
        vector_size=768,
        metadata_columns=metadata_columns,
        overwrite_existing=True,
    )

    print("✅ Table created successfully with schema:")
    print("  - langchain_id (UUID, primary key)")
    print("  - content (TEXT)")
    print("  - embedding (VECTOR(768))")
    print("  - langchain_metadata (JSONB)")
    print("  + 9 custom metadata columns")

    await engine.close()
    print("🔌 Closed database connection")


if __name__ == "__main__":
    try:
        asyncio.run(drop_and_recreate())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
