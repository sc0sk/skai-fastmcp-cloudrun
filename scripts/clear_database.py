#!/usr/bin/env python3
"""Clear speeches and speech_chunks tables to prepare for fresh ingestion."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_google_cloud_sql_pg import PostgresEngine


async def clear_tables():
    """Truncate speeches and speech_chunks tables."""
    print("Connecting to Cloud SQL...")

    engine = await PostgresEngine.afrom_instance(
        project_id=os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun"),
        region=os.getenv("GCP_REGION", "us-central1"),
        instance=os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2"),
        database=os.getenv("CLOUDSQL_DATABASE", "hansard"),
    )

    async with engine._pool.connect() as conn:
        # Check current counts
        speech_count = await conn.fetchval("SELECT COUNT(*) FROM speeches")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM speech_chunks")

        print(f"\nCurrent state:")
        print(f"  speeches: {speech_count} rows")
        print(f"  speech_chunks: {chunk_count} rows")

        # Truncate tables
        print(f"\nTruncating tables...")
        await conn.execute("TRUNCATE TABLE speech_chunks CASCADE")
        await conn.execute("TRUNCATE TABLE speeches CASCADE")

        # Verify
        speech_count_after = await conn.fetchval("SELECT COUNT(*) FROM speeches")
        chunk_count_after = await conn.fetchval("SELECT COUNT(*) FROM speech_chunks")

        print(f"\nAfter truncation:")
        print(f"  speeches: {speech_count_after} rows")
        print(f"  speech_chunks: {chunk_count_after} rows")
        print(f"\n✅ Tables cleared successfully")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(clear_tables())
