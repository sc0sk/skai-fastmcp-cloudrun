#!/usr/bin/env python3
"""Add missing columns to speeches table."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.metadata_store import get_default_metadata_store

async def main():
    """Add missing columns."""
    print("Adding missing columns to speeches table...")

    metadata_store = await get_default_metadata_store()
    conn = await metadata_store._get_connection()

    try:
        # Add default to speech_id if needed
        try:
            await conn.execute("""
                ALTER TABLE speeches
                ALTER COLUMN speech_id SET DEFAULT gen_random_uuid()::text
            """)
            print("✅ Added default to speech_id column")
        except Exception as e:
            print(f"⚠️  Could not set default for speech_id: {e}")

        # Add electorate column if missing
        await conn.execute("""
            ALTER TABLE speeches
            ADD COLUMN IF NOT EXISTS electorate TEXT
        """)
        print("✅ Added electorate column")

        # Add content_hash column if missing
        await conn.execute("""
            ALTER TABLE speeches
            ADD COLUMN IF NOT EXISTS content_hash TEXT UNIQUE
        """)
        print("✅ Added content_hash column")

        # Add topic_tags column if missing
        await conn.execute("""
            ALTER TABLE speeches
            ADD COLUMN IF NOT EXISTS topic_tags TEXT[]
        """)
        print("✅ Added topic_tags column")

        print("\n✅ All columns added successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
