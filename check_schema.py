#!/usr/bin/env python3
"""Check langchain_vector_store table schema."""

import asyncio
from langchain_google_cloud_sql_pg import PostgresEngine


async def check_schema():
    """Check the langchain_vector_store table schema."""
    # Connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db-v2"
    database = "hansard"

    print(f"Connecting to Cloud SQL...")
    print(f"  Project: {project_id}")
    print(f"  Instance: {instance}")
    print(f"  Database: {database}")

    # Create engine (uses IAM authentication automatically)
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database
    )

    # Get a connection from the pool
    async with engine._pool.connect() as conn:
        # Query table schema
        rows = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'langchain_vector_store'
            ORDER BY ordinal_position
        """)

        print("\nTable: langchain_vector_store")
        print("=" * 60)
        if not rows:
            print("❌ Table does not exist or has no columns!")
        else:
            for row in rows:
                col_name = row["column_name"]
                col_type = row["data_type"]
                max_len = row["character_maximum_length"]
                if max_len:
                    print(f"{col_name}: {col_type}({max_len})")
                else:
                    print(f"{col_name}: {col_type}")

        # Count rows
        count = await conn.fetchval("SELECT COUNT(*) FROM langchain_vector_store")
        print(f"\nTotal rows: {count}")

    # Close the engine
    await engine.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
