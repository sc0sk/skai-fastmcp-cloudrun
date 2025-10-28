#!/usr/bin/env python3
"""
T001-T004: Database setup using Cloud SQL Connector with IAM auth.
Creates fresh database, enables pgvector, and creates langchain-postgres schema.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text, create_engine, inspect
from google.cloud.sql.connector import Connector


def get_engine(database="postgres"):
    """Create SQLAlchemy engine with Cloud SQL Connector IAM auth."""
    connector = Connector()

    def getconn():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db=database,
            enable_iam_auth=True,
        )

    return create_engine("postgresql+pg8000://", creator=getconn)


def t001_create_database():
    """T001: Create fresh database and enable pgvector."""
    print("🔧 [T001] Creating fresh database...")

    # Connect to postgres default DB to create new DB
    engine = get_engine(database="postgres")

    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("DROP DATABASE IF EXISTS hansard_db_fresh;")
        )
        print("  ✅ Dropped old database (if exists)")

        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE DATABASE hansard_db_fresh;")
        )
        print("  ✅ Created database: hansard_db_fresh")

    engine.dispose()

    # Now connect to new database and enable pgvector
    print("\n🔧 [T001] Enabling pgvector extension...")
    engine = get_engine(database="hansard_db_fresh")

    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE EXTENSION IF NOT EXISTS vector;")
        )
        print("  ✅ pgvector extension enabled")

    engine.dispose()


def t002_create_schema():
    """T002: Create langchain-postgres schema tables."""
    print("\n🔧 [T002] Creating langchain-postgres schema...")

    engine = get_engine(database="hansard_db_fresh")

    schema_sql = """
    -- Create collection table
    CREATE TABLE IF NOT EXISTS langchain_pg_collection (
        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT UNIQUE NOT NULL,
        cmetadata JSONB
    );

    -- Create embedding table
    CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
        id TEXT PRIMARY KEY,
        collection_id UUID REFERENCES langchain_pg_collection(uuid) 
            ON DELETE CASCADE,
        embedding VECTOR(768),
        document TEXT NOT NULL,
        cmetadata JSONB NOT NULL
    );

    -- Create HNSW index for fast vector search
    CREATE INDEX IF NOT EXISTS idx_embedding_hnsw 
    ON langchain_pg_embedding 
    USING HNSW (embedding VECTOR (768) ops=vector_cosine_ops);

    -- Create index on collection_id for fast lookups
    CREATE INDEX IF NOT EXISTS idx_embedding_collection_id 
    ON langchain_pg_embedding (collection_id);

    -- Create GIN index on metadata for filtering
    CREATE INDEX IF NOT EXISTS idx_embedding_metadata 
    ON langchain_pg_embedding USING gin (cmetadata);
    """

    with engine.connect() as conn:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
        conn.commit()
        print("  ✅ langchain_pg_collection table created")
        print("  ✅ langchain_pg_embedding table created")
        print("  ✅ HNSW index created on embedding column")
        print("  ✅ GIN index created on metadata")

    engine.dispose()


def t003_create_collection():
    """T003: Create hansard collection record."""
    print("\n🔧 [T003] Creating collection record...")

    engine = get_engine(database="hansard_db_fresh")

    with engine.connect() as conn:
        result = conn.execute(
            text("""
            INSERT INTO langchain_pg_collection (name, cmetadata)
            VALUES ('hansard', :metadata)
            RETURNING uuid;
            """),
            {
                "metadata": (
                    '{"version": "1.0", "source": "data/hansard_converted", '
                    '"created": "2025-10-26"}'
                )
            },
        )
        collection_uuid = result.scalar_one()
        conn.commit()
        print(f"  ✅ Collection created: hansard")
        print(f"     UUID: {collection_uuid}")

    engine.dispose()


def t004_verify_schema():
    """T004: Verify database setup."""
    print("\n🔧 [T004] Verifying database setup...")

    engine = get_engine(database="hansard_db_fresh")

    with engine.connect() as conn:
        # Check tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"  ✅ Tables: {', '.join(sorted(tables))}")

        # Check indexes
        indexes = {}
        for table in tables:
            indexes[table] = [idx['name'] for idx in inspector.get_indexes(table)]
        print(f"  ✅ Indexes on langchain_pg_embedding: "
              f"{', '.join(indexes.get('langchain_pg_embedding', []))}")

        # Check extensions
        result = conn.execute(text("SELECT extname FROM pg_extension;"))
        exts = [row[0] for row in result]
        print(f"  ✅ Extensions: {', '.join(sorted(exts))}")

        # Check collection exists
        result = conn.execute(
            text("SELECT uuid, name FROM langchain_pg_collection;")
        )
        rows = result.fetchall()
        print(f"  ✅ Collections: {len(rows)} record(s)")
        for uuid, name in rows:
            print(f"     - {name}: {uuid}")

        # Check constraint
        result = conn.execute(
            text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints
            WHERE table_name = 'langchain_pg_embedding'
            AND constraint_type = 'FOREIGN KEY';
            """)
        )
        fks = [row[0] for row in result]
        print(f"  ✅ Foreign keys: {len(fks)} constraint(s)")

    engine.dispose()

    print("\n✨ Database setup complete!")
    print("   - Database: hansard_db_fresh")
    print("   - Tables: langchain_pg_collection, langchain_pg_embedding")
    print("   - Indexes: HNSW (vectors), GIN (metadata)")
    print("   - Collection: hansard (ready for population)")


if __name__ == "__main__":
    try:
        t001_create_database()
        t002_create_schema()
        t003_create_collection()
        t004_verify_schema()
        print("\n✅ Tasks T001-T004 completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
