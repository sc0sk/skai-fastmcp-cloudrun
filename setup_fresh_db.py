#!/usr/bin/env python3
"""
TDD-based setup for fresh hansard database with langchain-postgres schema.
Creates DB, tables, and enables pgvector.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text, create_engine
from google.cloud.sql.connector import Connector

def create_fresh_database():
    """Create fresh hansard_db_fresh database."""
    print("🔧 [1/4] Creating fresh database...")
    
    # Connect to postgres default DB to create new DB
    connector = Connector()
    
    def getconn_postgres():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db="postgres",
            enable_iam_auth=True,
        )
    
    engine = create_engine("postgresql+pg8000://", creator=getconn_postgres)
    
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("DROP DATABASE IF EXISTS hansard_db_fresh;")
        )
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE DATABASE hansard_db_fresh;")
        )
        print("✅ Database created: hansard_db_fresh")
    
    engine.dispose()


def enable_pgvector():
    """Enable pgvector extension in new database."""
    print("🔧 [2/4] Enabling pgvector extension...")
    
    connector = Connector()
    
    def getconn_fresh():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db="hansard_db_fresh",
            enable_iam_auth=True,
        )
    
    engine = create_engine("postgresql+pg8000://", creator=getconn_fresh)
    
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE EXTENSION IF NOT EXISTS vector;")
        )
        print("✅ pgvector extension enabled")
    
    engine.dispose()


def create_langchain_schema():
    """Create langchain-postgres schema tables."""
    print("🔧 [3/4] Creating langchain-postgres schema...")
    
    connector = Connector()
    
    def getconn_fresh():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db="hansard_db_fresh",
            enable_iam_auth=True,
        )
    
    engine = create_engine("postgresql+pg8000://", creator=getconn_fresh)
    
    schema_sql = """
    CREATE TABLE IF NOT EXISTS langchain_pg_collection (
        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT UNIQUE NOT NULL,
        cmetadata JSONB
    );
    
    CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
        id TEXT PRIMARY KEY,
        collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
        embedding VECTOR(768),
        document TEXT,
        cmetadata JSONB
    );
    
    CREATE INDEX ON langchain_pg_embedding USING HNSW (embedding VECTOR (768) ops=vector_cosine_ops);
    """
    
    with engine.connect() as conn:
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
        conn.commit()
        print("✅ langchain-postgres schema created")
    
    engine.dispose()


def verify_schema():
    """Verify schema was created."""
    print("🔧 [4/4] Verifying schema...")
    
    connector = Connector()
    
    def getconn_fresh():
        return connector.connect(
            "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
            "pg8000",
            user=os.getenv("CLOUD_SQL_USER", "postgres"),
            db="hansard_db_fresh",
            enable_iam_auth=True,
        )
    
    engine = create_engine("postgresql+pg8000://", creator=getconn_fresh)
    
    with engine.connect() as conn:
        # Check tables exist
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
        print(f"✅ Tables created: {', '.join(tables)}")
        
        # Check extensions
        result = conn.execute(text("SELECT extname FROM pg_extension;"))
        exts = [row[0] for row in result]
        print(f"✅ Extensions: {', '.join(exts)}")
    
    engine.dispose()


if __name__ == "__main__":
    try:
        create_fresh_database()
        enable_pgvector()
        create_langchain_schema()
        verify_schema()
        print("\n✨ Fresh database setup complete!")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
