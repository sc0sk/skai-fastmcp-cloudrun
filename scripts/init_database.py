#!/usr/bin/env python3
"""
Initialize Cloud SQL database schema for Hansard RAG system.

This script creates:
1. pgvector extension
2. speeches table (metadata storage)
3. speech_chunks table (vector storage with 768-dim embeddings)
4. HNSW index on speech_chunks for fast similarity search

Usage:
    python scripts/init_database.py

Prerequisites:
    - Cloud SQL instance running
    - Cloud SQL Proxy running OR direct connection
    - Environment variables set (GCP_PROJECT_ID, CLOUDSQL_INSTANCE, etc.)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
REGION = os.getenv("GCP_REGION", "us-central1")
INSTANCE = os.getenv("CLOUDSQL_INSTANCE", "hansard-db")
DATABASE = os.getenv("CLOUDSQL_DATABASE", "hansard")
USER = os.getenv("CLOUDSQL_USER", "postgres")


async def init_database():
    """Initialize database schema."""
    print("🔧 Initializing Hansard RAG Database")
    print("=" * 50)
    print(f"Project: {PROJECT_ID}")
    print(f"Instance: {INSTANCE}")
    print(f"Database: {DATABASE}")
    print("")

    connector = None

    try:
        # Connect to database using Cloud SQL Python Connector
        print("📡 Connecting to database via Cloud SQL Python Connector...")
        loop = asyncio.get_running_loop()
        connector = Connector(loop=loop)

        # Use IAM authentication (no password required)
        iam_user = "scott.coleman@aph.gov.au"
        conn = await connector.connect_async(
            f"{PROJECT_ID}:{REGION}:{INSTANCE}",
            "asyncpg",
            user=iam_user,
            db=DATABASE,
            enable_iam_auth=True,
        )

        print("✅ Connected successfully")
        print("")

        # 1. Enable pgvector extension
        print("🔌 Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Verify pgvector
        version = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )
        print(f"✅ pgvector v{version} enabled")
        print("")

        # 2. Create speeches table
        print("📊 Creating speeches table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS speeches (
                speech_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title VARCHAR(500) NOT NULL,
                full_text TEXT NOT NULL,
                speaker VARCHAR(200) NOT NULL,
                party VARCHAR(100) NOT NULL,
                chamber VARCHAR(50) NOT NULL CHECK (chamber IN ('House of Representatives', 'Senate')),
                electorate VARCHAR(100),
                state VARCHAR(3) CHECK (state IN ('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')),
                date DATE NOT NULL,
                hansard_reference VARCHAR(500) NOT NULL,
                word_count INTEGER,
                content_hash VARCHAR(64) UNIQUE NOT NULL,
                topic_tags TEXT[],
                source_url VARCHAR(1000),
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT electorate_chamber_check CHECK (
                    (chamber = 'Senate' AND electorate IS NULL) OR
                    (chamber = 'House of Representatives' AND electorate IS NOT NULL)
                )
            )
        """)
        print("✅ speeches table created")

        # Create indexes on speeches
        print("🔍 Creating indexes on speeches table...")
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speeches_speaker ON speeches(speaker)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speeches_party ON speeches(party)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speeches_chamber ON speeches(chamber)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speeches_date ON speeches(date)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speeches_content_hash ON speeches(content_hash)"
        )
        print("✅ Indexes created on speeches table")
        print("")

        # 3. Create speech_chunks table with vector column
        print("📦 Creating speech_chunks table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS speech_chunks (
                chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                speech_id UUID NOT NULL REFERENCES speeches(speech_id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_size INTEGER NOT NULL,
                embedding vector(768) NOT NULL,

                -- Denormalized metadata for filtering
                speaker VARCHAR(200) NOT NULL,
                party VARCHAR(100) NOT NULL,
                chamber VARCHAR(50) NOT NULL,
                state VARCHAR(3),
                date DATE NOT NULL,
                hansard_reference VARCHAR(500) NOT NULL,

                UNIQUE(speech_id, chunk_index)
            )
        """)
        print("✅ speech_chunks table created with 768-dim vector column")

        # Create HNSW index for vector similarity search
        print("🚀 Creating HNSW index on embeddings...")
        print("   (This may take a few moments...)")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_speech_chunks_embedding_hnsw
            ON speech_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 24, ef_construction = 100)
        """)
        print("✅ HNSW index created (m=24, ef_construction=100)")

        # Create other indexes
        print("🔍 Creating indexes on speech_chunks table...")
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speech_chunks_speech_id ON speech_chunks(speech_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speech_chunks_speaker ON speech_chunks(speaker)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_speech_chunks_date ON speech_chunks(date)"
        )
        print("✅ Indexes created on speech_chunks table")
        print("")

        # Get table info
        speeches_count = await conn.fetchval("SELECT COUNT(*) FROM speeches")
        chunks_count = await conn.fetchval("SELECT COUNT(*) FROM speech_chunks")

        print("=" * 50)
        print("✅ Database Schema Initialized Successfully!")
        print("=" * 50)
        print("")
        print("Tables Created:")
        print(f"  - speeches: {speeches_count} rows")
        print(f"  - speech_chunks: {chunks_count} rows (with 768-dim vectors)")
        print("")
        print("Indexes Created:")
        print("  - HNSW index on speech_chunks.embedding")
        print("  - B-tree indexes on metadata columns")
        print("")
        print("Next Steps:")
        print("1. Run ingestion CLI:")
        print("   python scripts/ingest_hansard.py --directory data/sk-hansard")
        print("")
        print("2. Start MCP server:")
        print("   fastmcp dev src/server.py")
        print("")

        await conn.close()
        if connector:
            await connector.close_async()
        return 0

    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"❌ Database '{DATABASE}' does not exist")
        print(f"   Create it first:")
        print(f"   gcloud sql databases create {DATABASE} --instance={INSTANCE}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(init_database())
    sys.exit(exit_code)
