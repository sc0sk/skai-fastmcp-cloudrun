"""Apply migration to add chunk_id column to speech_chunks table."""

import asyncio
import os
from langchain_google_cloud_sql_pg import PostgresEngine

async def apply_migration():
    """Apply migration using Cloud SQL Python Connector."""

    # Get connection details from environment
    project_id = os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    region = os.getenv("GCP_REGION", "us-central1")
    instance = os.getenv("CLOUDSQL_INSTANCE", "hansard-db-v2")
    database = os.getenv("CLOUDSQL_DATABASE", "hansard")

    print(f"📦 Connecting to Cloud SQL: {project_id}:{region}:{instance}/{database}")

    # Create engine using IAM authentication
    engine = await PostgresEngine.afrom_instance(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database,
    )

    print("✅ Connected to Cloud SQL")

    # Read migration SQL
    with open("migrate_add_chunk_id.sql", "r") as f:
        migration_sql = f.read()

    print("🔄 Applying migration...")

    # Execute migration
    async with engine._pool.connect() as conn:
        result = await conn.execute(migration_sql)
        await conn.commit()
        print(f"✅ Migration applied successfully")

    # Verify the column exists
    print("\n🔍 Verifying chunk_id column...")
    async with engine._pool.connect() as conn:
        result = await conn.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'speech_chunks'
            AND column_name IN ('chunk_id', 'speech_id', 'chunk_index')
            ORDER BY column_name;
        """)
        columns = result.fetchall()
        print("\nColumns in speech_chunks table:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")

    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(apply_migration())
