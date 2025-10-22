#!/usr/bin/env python3
"""Test search functionality directly against Cloud Run MCP server."""

import asyncio
import httpx
import json


async def test_search():
    """Test the search tool via direct HTTP calls to Cloud Run."""

    base_url = "https://mcp.simonkennedymp.com.au"

    print("🧪 Testing Search Functionality\n")
    print("=" * 60)

    # Test 1: Semantic search only (no filters)
    print("\n1️⃣  Test: Semantic search - 'cost of living and inflation'")
    print("-" * 60)

    search_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {
                "query": "cost of living and inflation",
                "limit": 3
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json=search_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 401:
                print("❌ Authentication required - need OAuth token")
                print("\nThis is expected - the server requires GitHub OAuth.")
                print("Let me try a different approach...")
                return False

            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")

            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    print(f"\n✅ Found {len(content)} results!")
                    for i, item in enumerate(content[:3], 1):
                        if "text" in item:
                            preview = item["text"][:200]
                            print(f"\n  Result {i}: {preview}...")
                    return True
                else:
                    print("\n⚠️  No results returned")
                    return False
            else:
                print("\n⚠️  Unexpected response format")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def test_via_mcp_sdk():
    """Test using MCP SDK directly (bypassing auth for testing)."""
    print("\n\n2️⃣  Test: Direct database query (bypass MCP)")
    print("-" * 60)

    # Import our search function directly
    import sys
    import os
    sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun')

    # Set environment variables
    os.environ["GCP_PROJECT_ID"] = "skai-fastmcp-cloudrun"
    os.environ["GCP_REGION"] = "us-central1"
    os.environ["CLOUDSQL_INSTANCE"] = "hansard-db-v2"
    os.environ["CLOUDSQL_DATABASE"] = "hansard"
    os.environ["GCP_PROJECT_NUMBER"] = "666924716777"

    try:
        from src.tools.search import search_speeches

        print("Searching for: 'cost of living and inflation'")
        results = await search_speeches(
            query="cost of living and inflation",
            limit=3
        )

        print(f"\n✅ Found {len(results)} results!")

        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    Speaker: {result.get('speaker', 'N/A')}")
            print(f"    Date: {result.get('date', 'N/A')}")
            print(f"    Relevance: {result.get('relevance_score', 0):.2f}")
            print(f"    Excerpt: {result.get('excerpt', '')[:150]}...")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    # Test 1: Via HTTP (will fail due to auth)
    await test_search()

    # Test 2: Direct function call (should work)
    await test_via_mcp_sdk()


if __name__ == "__main__":
    asyncio.run(main())
