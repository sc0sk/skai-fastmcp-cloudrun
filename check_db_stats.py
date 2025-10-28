#!/usr/bin/env python3
"""Check which files have already been ingested."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from src.storage.metadata_store import MetadataStore


async def main():
    """Check database for ingested speeches."""
    
    os.environ.setdefault("USE_IAM_AUTH", "1")
    
    store = MetadataStore()
    
    # Get stats
    stats = await store.get_stats()
    
    print(f"📊 Database Statistics:")
    print(f"   Total speeches: {stats['speech_count']}")
    print(f"   Unique speakers: {stats['unique_speakers']}")
    print(f"   Date range: {stats.get('earliest_date')} to {stats.get('latest_date')}")
    print(f"\n   Party breakdown:")
    for party, count in stats.get('party_breakdown', {}).items():
        print(f"      {party}: {count}")
    
    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
