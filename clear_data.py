#!/usr/bin/env python3
"""Clear all data from speeches and vector embeddings, then re-ingest."""

import asyncio
from sqlalchemy import text
from src.storage.metadata_store import get_default_metadata_store


async def clear_data():
    """Delete all data from speeches and langchain_pg_embedding tables."""
    
    store = await get_default_metadata_store()
    
    def _clear(conn):
        print("🗑️  Deleting all speeches...")
        result = conn.execute(text("DELETE FROM speeches"))
        print(f"✅ Deleted {result.rowcount} speeches")
        
        print("\n🗑️  Deleting all vector embeddings...")
        result = conn.execute(text("DELETE FROM langchain_pg_embedding"))
        print(f"✅ Deleted {result.rowcount} embeddings")
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM speeches"))
        count = result.scalar()
        print(f"\n✅ Speeches table now has {count} rows")
        
        result = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding"))
        count = result.scalar()
        print(f"✅ Embeddings table now has {count} rows")
    
    await store._run_in_connection(_clear)
    print("\n✅ Data cleared! Ready to re-ingest.")


if __name__ == "__main__":
    asyncio.run(clear_data())
