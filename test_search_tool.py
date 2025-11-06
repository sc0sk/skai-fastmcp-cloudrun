#!/usr/bin/env python3
"""Test the search tool to trigger database connection."""
import asyncio
import os
import sys

# Set environment to use IAM auth
os.environ['USE_IAM_AUTH'] = 'true'
os.environ['K_SERVICE'] = 'test-mcp-inspector'

async def test_local_search():
    """Test search tool locally to see database errors."""
    print("=== Testing Search Tool (triggers database connection) ===\n")

    try:
        from src.tools.search import search_hansard_speeches

        print("Calling search_hansard_speeches(query='housing', limit=2)...")
        result = await search_hansard_speeches(query="housing", limit=2)

        print("\n✅ SUCCESS!")
        print(f"Found {result.get('total_count', 0)} speeches")
        return True

    except Exception as e:
        print(f"\n❌ FAILED with error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_local_search())
    sys.exit(0 if success else 1)
