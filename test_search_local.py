#!/usr/bin/env python3
"""Test search functionality locally without OAuth."""

import asyncio
import os

# Set environment variables
os.environ["GCP_PROJECT_ID"] = "skai-fastmcp-cloudrun"
os.environ["GCP_REGION"] = "us-central1"
os.environ["CLOUDSQL_INSTANCE"] = "hansard-db-v2"
os.environ["CLOUDSQL_DATABASE"] = "hansard"
os.environ["VERTEX_AI_LOCATION"] = "us-central1"
os.environ["GCP_PROJECT_NUMBER"] = "666924716777"

from src.tools.search import search_speeches


async def main():
    """Test search functionality."""
    print("🔍 Testing Hansard speech search...")
    print("=" * 80)

    # Test search
    query = "climate change and renewable energy"
    print(f"\n📝 Query: '{query}'")
    print(f"🔄 Searching...")

    try:
        results = await search_speeches(query=query, limit=3)

        print(f"\n✅ Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Speaker: {result['speaker']}")
            print(f"  Party: {result['party']}")
            print(f"  Chamber: {result['chamber']}")
            print(f"  Date: {result['date']}")
            print(f"  Relevance: {result['relevance_score']:.3f}")
            print(f"  Excerpt: {result['excerpt'][:150]}...")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
