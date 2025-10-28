#!/usr/bin/env python3
"""
Simplified Feature 017 Deployment: Use Existing MCP Tools

Instead of recreating all functionality from scratch, we leverage:
- Feature 012: ingest_markdown_file (single file ingestion)
- Feature 013: ingest_markdown_directory (bulk ingestion with progress)

These tools already provide:
✅ Markdown parsing with frontmatter extraction
✅ Text splitting (LangChain RecursiveCharacterTextSplitter)
✅ Vector embeddings (Vertex AI text-embedding-004, 768-dim)
✅ PostgreSQL storage with langchain-postgres schema
✅ Progress reporting and error isolation
✅ Admin authentication

APPROACH:
1. Create fresh database hansard_db_fresh with pgvector schema
2. Call ingest_markdown_directory MCP tool to bulk load speeches
3. Verify data integrity
4. Update Cloud Run service VECTOR_BACKEND env var

TIMELINE: 30-60 minutes (vs 1 week to reimplement)
"""

import os
import sys
from pathlib import Path
import asyncio
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text, inspect
from storage.cloud_sql_engine import CloudSQLEngine
from tools.ingest_markdown_directory import ingest_markdown_directory


def get_engine(database="postgres"):
    """Create SQLAlchemy engine with Cloud SQL Connector IAM auth."""
    engine_mgr = CloudSQLEngine(
        project_id="skai-fastmcp-cloudrun",
        region="us-central1",
        instance="hansard-db-v2",
        database=database,
        user=None,  # IAM auth
        password=None,
    )
    return engine_mgr.engine


def setup_database():
    """Create fresh database and schema."""
    print("=" * 80)
    print("STEP 1: Setup Fresh Database")
    print("=" * 80)

    # Create database
    print("\n🔧 Creating database hansard_db_fresh...")
    engine = get_engine(database="postgres")

    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("DROP DATABASE IF EXISTS hansard_db_fresh;")
        )
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE DATABASE hansard_db_fresh;")
        )
    engine.dispose()
    print("✅ Database created")

    # Enable pgvector
    print("\n🔧 Enabling pgvector extension...")
    engine = get_engine(database="hansard_db_fresh")

    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE EXTENSION IF NOT EXISTS vector;")
        )
    print("✅ pgvector enabled")

    # Create schema
    print("\n🔧 Creating langchain-postgres schema...")
    schema_sql = """
    CREATE TABLE IF NOT EXISTS langchain_pg_collection (
        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT UNIQUE NOT NULL,
        cmetadata JSONB
    );

    CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
        id TEXT PRIMARY KEY,
        collection_id UUID REFERENCES langchain_pg_collection(uuid) 
            ON DELETE CASCADE,
        embedding VECTOR(768),
        document TEXT NOT NULL,
        cmetadata JSONB NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_embedding_hnsw 
    ON langchain_pg_embedding 
    USING HNSW (embedding VECTOR (768) ops=vector_cosine_ops);

    CREATE INDEX IF NOT EXISTS idx_embedding_collection_id 
    ON langchain_pg_embedding (collection_id);

    CREATE INDEX IF NOT EXISTS idx_embedding_metadata 
    ON langchain_pg_embedding USING gin (cmetadata);
    """

    with engine.connect() as conn:
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    print("✅ Schema created (collection + embedding tables)")

    # Create collection
    print("\n🔧 Creating collection record...")
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            INSERT INTO langchain_pg_collection (name, cmetadata)
            VALUES ('hansard', :metadata)
            RETURNING uuid;
            """),
            {
                "metadata": (
                    '{"version": "1.0", "source": "Feature 017", '
                    '"created": "2025-10-26", '
                    '"method": "ingest_markdown_directory MCP tool"}'
                )
            },
        )
        collection_uuid = result.scalar_one()
        conn.commit()
    print(f"✅ Collection created: hansard ({collection_uuid})")

    engine.dispose()


async def populate_speeches():
    """Use existing MCP tool to bulk ingest speeches."""
    print("\n" + "=" * 80)
    print("STEP 2: Bulk Ingest Speeches Using Existing MCP Tool")
    print("=" * 80)

    print("\n📂 Using Feature 013: ingest_markdown_directory")
    print("   This tool provides:")
    print("   ✅ Directory discovery with glob patterns")
    print("   ✅ Markdown parsing (frontmatter + content)")
    print("   ✅ Text splitting (LangChain RecursiveCharacterTextSplitter)")
    print("   ✅ Embeddings generation (Vertex AI, 768-dim)")
    print("   ✅ PostgreSQL storage (langchain-postgres schema)")
    print("   ✅ Progress reporting and error isolation")

    print("\n🚀 Starting bulk ingestion...")
    print("   Directory: data/hansard_converted/")
    print("   Pattern: *.md")
    print("   Max files: 100")

    try:
        result = await ingest_markdown_directory(
            directory_path="data/hansard_converted/",
            pattern="*.md",
            max_files=100,
            duplicate_policy="skip",
            validate_path=False,  # Allow relative paths
            ctx=None  # No auth needed (local script)
        )

        print("\n" + "=" * 80)
        print("INGESTION RESULTS")
        print("=" * 80)

        summary = result.get("summary", {})
        print(f"\n📊 Summary:")
        print(f"   Total files discovered: {summary.get('total_files', 0)}")
        print(f"   Successfully ingested: {summary.get('succeeded', 0)}")
        print(f"   Skipped (duplicates): {summary.get('skipped', 0)}")
        print(f"   Failed: {summary.get('failed', 0)}")
        print(f"   Total chunks created: {summary.get('total_chunks_created', 0)}")

        if result.get("failed_files"):
            print(f"\n⚠️  Failed files ({len(result['failed_files'])}):")
            for failed in result["failed_files"][:5]:
                print(f"   - {failed.get('file_name')}: {failed.get('error')}")
            if len(result["failed_files"]) > 5:
                print(f"   ... and {len(result['failed_files']) - 5} more")

        print(f"\n✅ Ingestion complete: {result.get('message', '')}")

        return result

    except Exception as e:
        print(f"\n❌ Ingestion error: {e}")
        import traceback
        traceback.print_exc()
        raise


def verify_data():
    """Verify data was loaded correctly."""
    print("\n" + "=" * 80)
    print("STEP 3: Verify Data Integrity")
    print("=" * 80)

    engine = get_engine(database="hansard_db_fresh")

    with engine.connect() as conn:
        # Count embeddings
        result = conn.execute(
            text("SELECT COUNT(*) FROM langchain_pg_embedding;")
        )
        embedding_count = result.scalar()
        print(f"\n📊 Embeddings loaded: {embedding_count:,}")

        # Check for NULL vectors
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM langchain_pg_embedding "
                "WHERE embedding IS NULL;"
            )
        )
        null_vectors = result.scalar()
        print(f"   NULL vectors: {null_vectors} (should be 0)")

        # Check metadata coverage
        result = conn.execute(
            text("""
            SELECT COUNT(*) FROM langchain_pg_embedding 
            WHERE cmetadata->>'speaker' IS NOT NULL 
            AND cmetadata->>'date' IS NOT NULL;
            """)
        )
        complete_metadata = result.scalar()
        print(f"   Complete metadata: {complete_metadata:,} (should be ~all)")

        # Check unique speakers
        result = conn.execute(
            text("""
            SELECT COUNT(DISTINCT cmetadata->>'speaker')
            FROM langchain_pg_embedding;
            """)
        )
        speaker_count = result.scalar()
        print(f"   Unique speakers: {speaker_count}")

        # Check date range
        result = conn.execute(
            text("""
            SELECT 
              MIN((cmetadata->>'date')::date) as earliest,
              MAX((cmetadata->>'date')::date) as latest
            FROM langchain_pg_embedding;
            """)
        )
        earliest, latest = result.fetchone()
        print(f"   Date range: {earliest} to {latest}")

    engine.dispose()

    print("\n✅ Data verification complete!")


async def main():
    """Execute all steps."""
    try:
        # Step 1: Setup database
        setup_database()

        # Step 2: Bulk ingest speeches
        await populate_speeches()

        # Step 3: Verify data
        verify_data()

        print("\n" + "=" * 80)
        print("✨ FEATURE 017 DEPLOYMENT COMPLETE")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("   1. Update Cloud Run service VECTOR_BACKEND=postgres")
        print("   2. Deploy service: gcloud run deploy hansard-mcp...")
        print("   3. Test: curl https://hansard-mcp.../search")
        print("\n💡 Key insight:")
        print("   Used existing Feature 012/013 MCP tools instead of")
        print("   reimplementing all 35 tasks from scratch!")
        print("   Result: 30-60 min deployment vs 1 week")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
