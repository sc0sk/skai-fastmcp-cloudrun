#!/usr/bin/env python3
"""Simple dry-run to check migration status without complex IAM setup."""

import os
import sys

# Set environment
os.environ['GCP_PROJECT_ID'] = 'skai-fastmcp-cloudrun'
os.environ['GCP_REGION'] = 'us-central1'
os.environ['CLOUDSQL_INSTANCE'] = 'hansard-db-v2'
os.environ['CLOUDSQL_DATABASE'] = 'hansard'
os.environ['VECTOR_BACKEND'] = 'legacy'  # Use legacy to connect

sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun/src')

from src.storage.vector_store import VectorStoreService
from langchain_google_cloud_sql_pg import PostgresEngine

# Create engine using the working legacy method
engine = PostgresEngine.from_instance(
    project_id='skai-fastmcp-cloudrun',
    region='us-central1',
    instance='hansard-db-v2',
    database='hansard'
)

print("\n" + "=" * 70)
print("📊 DRY RUN: Migration Status Check")
print("=" * 70)

# Get the actual SQLAlchemy engine
import asyncio

async def check_db():
    # Create sync engine from the async engine
    await engine.ainit()
    
    # Use the internal sync engine
    actual_engine = engine._engine
    
    return actual_engine

sync_engine = asyncio.run(check_db())

# Check what tables exist
with sync_engine.connect() as conn:
    result = conn.execute("""
        SELECT table_name, 
               (SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = t.table_name 
                AND table_schema = 'public') as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    tables = list(result)
    print(f"\n✅ Found {len(tables)} tables in database:\n")
    for table, cols in tables:
        print(f"   • {table} ({cols} columns)")

# Check record counts for migration-relevant tables
print("\n" + "=" * 70)
print("📈 Record Counts (Migration Preview)")
print("=" * 70)

with sync_engine.connect() as conn:
    # Source table (legacy)
    try:
        result = conn.execute("SELECT COUNT(*) FROM hansard_speeches;")
        source_count = result.scalar()
        print(f"\n  SOURCE (will copy FROM here):")
        print(f"  • hansard_speeches (LEGACY):  {source_count:,} records ✅")
        
        # Show sample data structure
        result = conn.execute("""
            SELECT 
                array_length(embedding, 1) as vector_dim,
                langchain_metadata->>'date' as sample_date,
                langchain_metadata->>'house' as sample_house
            FROM hansard_speeches 
            LIMIT 1;
        """)
        row = result.fetchone()
        if row:
            print(f"    - Vector dimensions: {row[0]}")
            print(f"    - Sample metadata: date={row[1]}, house={row[2]}")
            
    except Exception as e:
        print(f"\n  ❌ ERROR reading hansard_speeches: {e}")
        source_count = 0
    
    # Target tables (new langchain-postgres)
    print(f"\n  TARGET (will copy TO here):")
    
    try:
        result = conn.execute("SELECT COUNT(*) FROM langchain_pg_collection;")
        coll_count = result.scalar()
        print(f"  • langchain_pg_collection (NEW): {coll_count:,} collections")
        
        if coll_count > 0:
            result = conn.execute("SELECT name, uuid FROM langchain_pg_collection;")
            for name, uuid in result:
                print(f"      - Collection: '{name}' (UUID: {uuid})")
    except Exception as e:
        print(f"  • langchain_pg_collection (NEW): ❌ Table doesn't exist yet")
        coll_count = 0
    
    try:
        result = conn.execute("SELECT COUNT(*) FROM langchain_pg_embedding;")
        embed_count = result.scalar()
        print(f"  • langchain_pg_embedding (NEW):  {embed_count:,} embeddings")
        
        if embed_count > 0:
            result = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT custom_id) as unique_ids,
                    array_length(embedding, 1) as vector_dim
                FROM langchain_pg_embedding
                LIMIT 1;
            """)
            row = result.fetchone()
            if row:
                print(f"      - Total records: {row[0]:,}")
                print(f"      - Unique custom_ids: {row[1]:,}")
                print(f"      - Vector dimensions: {row[2]}")
    except Exception as e:
        print(f"  • langchain_pg_embedding (NEW):  ❌ Table doesn't exist yet")
        embed_count = 0

# Migration assessment
print("\n" + "=" * 70)
print("🎯 Migration Assessment")
print("=" * 70)

if source_count == 0:
    print("\n⚠️  WARNING: Source table is empty! Nothing to migrate.")
elif not (coll_count >= 0):  # Table doesn't exist
    print(f"\n✅ READY TO MIGRATE:")
    print(f"   - {source_count:,} records will be copied")
    print(f"   - Target tables will be created automatically")
    print(f"   - Estimated time: ~{max(1, source_count // 2000)} minutes")
    print(f"   - Estimated batches: {(source_count + 99) // 100}")
elif embed_count == 0:
    print(f"\n✅ READY TO MIGRATE:")
    print(f"   - {source_count:,} records will be copied")
    print(f"   - Target tables exist but are empty")
    print(f"   - Estimated time: ~{max(1, source_count // 2000)} minutes")
    print(f"   - Estimated batches: {(source_count + 99) // 100}")
elif embed_count < source_count:
    print(f"\n⚠️  PARTIAL MIGRATION DETECTED:")
    print(f"   - Source: {source_count:,} records")
    print(f"   - Target: {embed_count:,} records")
    print(f"   - Missing: {source_count - embed_count:,} records")
    print(f"   - Re-running migration will be idempotent (safe)")
elif embed_count == source_count:
    print(f"\n✅ MIGRATION ALREADY COMPLETE:")
    print(f"   - Source: {source_count:,} records")
    print(f"   - Target: {embed_count:,} records")
    print(f"   - Status: Counts match! ✅")
    print(f"\n   You can now switch to new backend:")
    print(f"   gcloud run services update hansard-mcp-server \\")
    print(f"     --region=us-central1 \\")
    print(f"     --update-env-vars=VECTOR_BACKEND=postgres")
else:
    print(f"\n⚠️  UNEXPECTED STATE:")
    print(f"   - Source: {source_count:,} records")
    print(f"   - Target: {embed_count:,} records")
    print(f"   - Target has MORE records than source!")

print("\n" + "=" * 70)
print("📋 Next Steps")
print("=" * 70)

if source_count > 0 and embed_count == 0:
    print("""
1. Run the actual migration:
   cd /home/user/skai-fastmcp-cloudrun
   uv run python scripts/migrate_to_langchain_postgres.py --execute --progress

2. After migration completes, switch backend:
   gcloud run services update hansard-mcp-server \\
     --region=us-central1 \\
     --update-env-vars=VECTOR_BACKEND=postgres

3. Test the service works

4. If problems, instant rollback:
   gcloud run services update hansard-mcp-server \\
     --region=us-central1 \\
     --update-env-vars=VECTOR_BACKEND=legacy
""")
elif embed_count == source_count:
    print("""
✅ Migration already complete! You can:

1. Switch to new backend (if not already):
   gcloud run services update hansard-mcp-server \\
     --region=us-central1 \\
     --update-env-vars=VECTOR_BACKEND=postgres

2. Or stay on legacy backend (still works fine)
""")
else:
    print("""
Check the database state and run migration if needed.
See MIGRATION_EXPLAINED.md for full details.
""")

print("=" * 70)
