#!/usr/bin/env python3
"""Initialize LangChain-compatible schema using password authentication.

This script is for fresh database setup when IAM users haven't been configured yet.
Uses postgres user with password to create the initial schema.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
from google.cloud.sql.connector import Connector
from config import (
    DEFAULT_GCP_PROJECT_ID,
    DEFAULT_GCP_REGION,
    CLOUDSQL_INSTANCE_NAME,
    DEFAULT_CLOUDSQL_DATABASE,
    VECTOR_TABLE_NAME,
)


async def init_schema():
    """Initialize vector store table schema with password auth."""

    project_id = os.getenv("GCP_PROJECT_ID", DEFAULT_GCP_PROJECT_ID)
    region = os.getenv("GCP_REGION", DEFAULT_GCP_REGION)
    instance = os.getenv("CLOUDSQL_INSTANCE", CLOUDSQL_INSTANCE_NAME)
    database = os.getenv("CLOUDSQL_DATABASE", DEFAULT_CLOUDSQL_DATABASE)
    user = os.getenv("CLOUDSQL_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD")

    if not password:
        print("❌ Error: DATABASE_PASSWORD environment variable required")
        sys.exit(1)

    print(f"🔌 Connecting to Cloud SQL...")
    print(f"   Project: {project_id}")
    print(f"   Instance: {instance}")
    print(f"   Database: {database}")
    print(f"   User: {user}")

    # Initialize Cloud SQL Python Connector inside async context
    async with Connector() as connector:
        # Connect to Cloud SQL
        conn: asyncpg.Connection = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user=user,
            password=password,
            db=database,
        )

            print(f"\n📦 Enabling pgvector extension...")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print(f"   ✅ pgvector extension enabled")

            print(f"\n📊 Creating {VECTOR_TABLE_NAME} table...")

            # Create table with LangChain-compatible schema
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {VECTOR_TABLE_NAME} (
                    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding vector(768) NOT NULL,
                    langchain_metadata JSONB DEFAULT '{{}}'::jsonb,
                    speaker VARCHAR(200),
                    party VARCHAR(100),
                    chamber VARCHAR(50),
                    date DATE,
                    speech_type VARCHAR(100),
                    electorate VARCHAR(100),
                    speaker_id VARCHAR(20),
                    utterance_id VARCHAR(100),
                    debate TEXT
                );
            """)
            print(f"   ✅ Table created")

            print(f"\n🔍 Creating vector index (HNSW)...")
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {VECTOR_TABLE_NAME}_embedding_idx
                ON {VECTOR_TABLE_NAME}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 24, ef_construction = 100);
            """)
            print(f"   ✅ Vector index created")

            print(f"\n🔍 Creating metadata indexes...")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_speaker ON {VECTOR_TABLE_NAME}(speaker);")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_party ON {VECTOR_TABLE_NAME}(party);")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_chamber ON {VECTOR_TABLE_NAME}(chamber);")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_date ON {VECTOR_TABLE_NAME}(date);")
            print(f"   ✅ Metadata indexes created")

            print(f"\n✅ Schema initialized successfully!")
            print(f"\nTable structure:")
            print(f"  - langchain_id (UUID, primary key)")
            print(f"  - content (TEXT)")
            print(f"  - embedding (VECTOR(768))")
            print(f"  - langchain_metadata (JSONB)")
            print(f"  - speaker, party, chamber, date, speech_type, electorate, speaker_id, utterance_id, debate")

        finally:
            await conn.close()
            print(f"\n🔌 Closed database connection")


if __name__ == "__main__":
    try:
        asyncio.run(init_schema())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
