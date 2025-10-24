#!/usr/bin/env python3
"""Initialize schema using direct asyncpg connection."""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import VECTOR_TABLE_NAME


async def main():
    # Connect directly with asyncpg (no Connector)
    # SSL required for Cloud SQL public IP connections
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host='136.115.241.202',  # Public IP from gcloud sql instances describe
        port=5432,
        database='hansard',
        user='postgres',
        password='temporarypassword123',
        ssl=ssl_context,
    )

    try:
        print("🔌 Connected to Cloud SQL")

        print("📦 Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("   ✅ pgvector enabled")

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
        print("   ✅ Table created")

        print("🔍 Creating HNSW vector index...")
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {VECTOR_TABLE_NAME}_embedding_idx
            ON {VECTOR_TABLE_NAME}
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 24, ef_construction = 100);
        """)
        print("   ✅ Vector index created")

        print("🔍 Creating metadata indexes...")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_speaker ON {VECTOR_TABLE_NAME}(speaker);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_party ON {VECTOR_TABLE_NAME}(party);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_chamber ON {VECTOR_TABLE_NAME}(chamber);")
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{VECTOR_TABLE_NAME}_date ON {VECTOR_TABLE_NAME}(date);")
        print("   ✅ Metadata indexes created")

        print("\n✅ Schema initialized successfully!")

    finally:
        await conn.close()
        print("🔌 Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
