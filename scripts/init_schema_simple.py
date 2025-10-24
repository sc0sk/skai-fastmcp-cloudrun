#!/usr/bin/env python3
"""Initialize LangChain schema using password authentication."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
from google.cloud.sql.connector import Connector
from config import DEFAULT_GCP_PROJECT_ID, DEFAULT_GCP_REGION, CLOUDSQL_INSTANCE_NAME, DEFAULT_CLOUDSQL_DATABASE, VECTOR_TABLE_NAME


async def main():
    project_id = os.getenv("GCP_PROJECT_ID", DEFAULT_GCP_PROJECT_ID)
    region = os.getenv("GCP_REGION", DEFAULT_GCP_REGION)
    instance = os.getenv("CLOUDSQL_INSTANCE", CLOUDSQL_INSTANCE_NAME)
    database = os.getenv("CLOUDSQL_DATABASE", DEFAULT_CLOUDSQL_DATABASE)
    user = os.getenv("CLOUDSQL_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD")

    if not password:
        print("❌ Error: DATABASE_PASSWORD required")
        sys.exit(1)

    print(f"🔌 Connecting to {instance}...")

    connector = Connector()
    try:
        conn = await connector.connect_async(
            f"{project_id}:{region}:{instance}",
            "asyncpg",
            user=user,
            password=password,
            db=database,
        )

        print(f"📦 Enabling pgvector...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        print(f"📊 Creating {VECTOR_TABLE_NAME} table...")
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

        print(f"🔍 Creating vector index...")
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {VECTOR_TABLE_NAME}_embedding_idx
            ON {VECTOR_TABLE_NAME}
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 24, ef_construction = 100);
        """)

        print(f"🔍 Creating metadata indexes...")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_speaker ON {VECTOR_TABLE_NAME}(speaker);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_party ON {VECTOR_TABLE_NAME}(party);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_chamber ON {VECTOR_TABLE_NAME}(chamber);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_date ON {VECTOR_TABLE_NAME}(date);")

        print(f"✅ Schema initialized successfully!")

    finally:
        await conn.close()
        await connector.close_async()


if __name__ == "__main__":
    asyncio.run(main())
