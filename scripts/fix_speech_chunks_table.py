#!/usr/bin/env python3
"""Drop incompatible speech_chunks table to allow LangChain to recreate it."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.metadata_store import get_default_metadata_store

async def main():
    """Drop speech_chunks table."""
    print("=" * 80)
    print("Fixing speech_chunks Table for LangChain Compatibility")
    print("=" * 80)
    print()

    metadata_store = await get_default_metadata_store()
    conn = await metadata_store._get_connection()

    try:
        # Drop the existing speech_chunks table
        await conn.execute("DROP TABLE IF EXISTS speech_chunks CASCADE")
        print("✅ Dropped existing speech_chunks table")
        print("   (LangChain will recreate it with the correct schema)")
        print()
        print("=" * 80)
        print("Done! LangChain will auto-create the table on next chunk operation.")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
