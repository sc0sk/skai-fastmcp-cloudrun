#!/usr/bin/env python3
"""
Quick setup script using pgsql tools to create fresh database.
"""

import subprocess
import sys


def run_gcloud_sql(sql_statement, database="postgres"):
    """Execute SQL using gcloud sql connect."""
    cmd = [
        "gcloud", "sql", "connect", "hansard-db-v2",
        "--project=skai-fastmcp-cloudrun",
        "--database=" + database,
        "--user=postgres"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=sql_statement,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return False
        
        print(result.stdout)
        return True
    except subprocess.TimeoutExpired:
        print("Command timeout", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def setup_fresh_db():
    """Setup fresh database step by step."""
    print("📊 Setting up fresh hansard database...")
    
    # Step 1: Create database
    print("\n1️⃣ Creating database hansard_db_fresh...")
    sql1 = (
        "DROP DATABASE IF EXISTS hansard_db_fresh; "
        "CREATE DATABASE hansard_db_fresh;"
    )
    if not run_gcloud_sql(sql1, database="postgres"):
        return False
    
    # Step 2: Enable pgvector
    print("\n2️⃣ Enabling pgvector extension...")
    sql2 = "CREATE EXTENSION IF NOT EXISTS vector;"
    if not run_gcloud_sql(sql2, database="hansard_db_fresh"):
        return False
    
    # Step 3: Create langchain schema
    print("\n3️⃣ Creating langchain-postgres schema...")
    sql3 = """
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
    
    CREATE INDEX idx_embedding ON langchain_pg_embedding USING HNSW (embedding vector_cosine_ops);
    """
    if not run_gcloud_sql(sql3, database="hansard_db_fresh"):
        return False
    
    # Step 4: Verify
    print("\n4️⃣ Verifying schema...")
    sql4 = """
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema='public' AND table_type='BASE TABLE'
    ORDER BY table_name;
    """
    if not run_gcloud_sql(sql4, database="hansard_db_fresh"):
        return False
    
    print("\n✨ Fresh database setup complete!")
    return True


if __name__ == "__main__":
    if not setup_fresh_db():
        sys.exit(1)
