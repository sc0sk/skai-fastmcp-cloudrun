#!/usr/bin/env python3
"""Drop and recreate langchain_vector_store table with correct schema."""

import asyncio
from langchain_google_cloud_sql_pg import PostgresEngine


async def recreate_table():
    """Drop and recreate the table with correct schema."""
    # Connection parameters
    project_id = "skai-fastmcp-cloudrun"
    region = "us-central1"
    instance = "hansard-db-v2"
    database = "hansard"
    table_name = "langchain_vector_store"

    print(f"🔧 Recreating table: {table_name}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}\n")

    # Create engine
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database
    )

    # Drop existing table using SQL directly via the pool
    print(f"⚠️  Dropping existing table...")
    try:
        async with engine._pool.connect() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            await conn.commit()
        print(f"✅ Table dropped successfully")
    except Exception as e:
        print(f"❌ Error dropping table: {e}")
        print(f"   Attempting to continue anyway...")


    # Recreate table with correct schema
    print(f"\n🔧 Creating table with correct schema...")
    try:
        await engine.ainit_vectorstore_table(
            table_name=table_name,
            vector_size=768
        )
        print(f"✅ Table created successfully!")
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return

    # Verify table schema
    print(f"\n✅ Done! You can now run populate_hansard_speeches.py")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(recreate_table())
