#!/usr/bin/env python3
"""Check if database has speeches."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.metadata_store import get_default_metadata_store

async def main():
    """Check database contents."""
    print("=" * 80)
    print("Checking Database Contents")
    print("=" * 80)
    print()

    metadata_store = await get_default_metadata_store()
    conn = await metadata_store._get_connection()

    try:
        # Count speeches
        count = await conn.fetchval("SELECT COUNT(*) FROM speeches")
        print(f"✅ Total speeches in database: {count}")
        print()

        if count > 0:
            # Show sample speeches
            rows = await conn.fetch("""
                SELECT speech_id, title, speaker, date
                FROM speeches
                ORDER BY date DESC
                LIMIT 5
            """)

            print("Recent speeches:")
            print("-" * 80)
            for row in rows:
                print(f"  [{row['date']}] {row['title']}")
                print(f"    Speaker: {row['speaker']} | ID: {row['speech_id'][:8]}...")
            print()

        # Count chunks
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM speech_chunks")
        print(f"✅ Total speech chunks in database: {chunk_count}")
        print()

        if count == 0:
            print("⚠️  Database is empty - population may have failed")
        else:
            print(f"✅ Database successfully populated with {count} speeches and {chunk_count} chunks!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await conn.close()
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
