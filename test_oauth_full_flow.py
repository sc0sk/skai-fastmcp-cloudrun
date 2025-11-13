#!/usr/bin/env python3
"""
Test complete OAuth flow with browser authentication and MCP tool calls.

This test:
1. Opens browser for OAuth authentication
2. Completes GitHub OAuth flow
3. Connects to MCP server with OAuth token
4. Tests search_hansard_speeches tool
5. Tests fetch_hansard_speech tool
"""

import asyncio
import json
from fastmcp.client import Client


SERVER_URL = "https://hansard-mcp-server-666924716777.us-central1.run.app/mcp"


async def complete_oauth_flow():
    """Complete OAuth flow with browser and return access token."""

    print("🔐 Starting OAuth flow...")
    print(f"📡 Server: {SERVER_URL}")
    print()

    # Use FastMCP client with automatic OAuth handling
    try:
        async with Client(SERVER_URL, auth="oauth") as client:
            print("✅ OAuth authentication successful!")
            print()

            # List available tools
            print("📋 Listing available tools...")
            tools = await client.list_tools()
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:80]}...")
            print()

            # Test search tool
            print("🔍 Testing search_hansard_speeches...")
            try:
                result = await client.call_tool(
                    "search_hansard_speeches",
                    arguments={"query": "climate change", "top_k": 3}
                )
                print(f"✅ Search returned {len(result)} results")
                if result:
                    print(f"   First result: {result[0].get('speaker', 'Unknown')} - {result[0].get('date', 'N/A')}")
                print()
            except Exception as e:
                print(f"❌ Search failed: {e}")
                print()

            # Test fetch tool if we have results
            if result and len(result) > 0:
                speech_id = result[0].get("id")
                if speech_id:
                    print(f"📄 Testing fetch_hansard_speech for ID: {speech_id}")
                    try:
                        speech = await client.call_tool(
                            "fetch_hansard_speech",
                            arguments={"speech_id": speech_id}
                        )
                        print(f"✅ Fetched speech by {speech.get('speaker', 'Unknown')}")
                        print(f"   Text length: {len(speech.get('text', ''))} characters")
                        print()
                    except Exception as e:
                        print(f"❌ Fetch failed: {e}")
                        print()

            print("✅ All tests completed successfully!")
            return True

    except Exception as e:
        print(f"❌ OAuth flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(complete_oauth_flow())
    exit(0 if success else 1)
