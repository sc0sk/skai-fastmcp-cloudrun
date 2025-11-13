#!/usr/bin/env python3
"""Test OAuth flow against deployed Cloud Run server."""

import asyncio
from fastmcp.client import Client


async def test_oauth_flow():
    """Test OAuth authentication and tool access."""

    server_url = "https://hansard-mcp-server-355dd2atrq-uc.a.run.app/mcp"

    print(f"🔐 Connecting to {server_url}")
    print("⚠️  This will open a browser window for OAuth authentication")
    print()

    async with Client(server_url, auth="oauth") as client:
        print("✅ OAuth authentication successful!")
        print()

        # List available tools
        print("📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        # Test search tool
        print("🔍 Testing search_hansard_speeches...")
        result = await client.call_tool(
            "search_hansard_speeches",
            arguments={"query": "climate change", "top_k": 3}
        )
        print(f"Search returned {len(result)} results")
        print()

        # Test fetch tool if we have results
        if result and len(result) > 0:
            speech_id = result[0].get("id")
            print(f"📄 Testing fetch_hansard_speech for ID: {speech_id}")
            speech = await client.call_tool(
                "fetch_hansard_speech",
                arguments={"speech_id": speech_id}
            )
            print(f"Fetched speech: {speech.get('speaker', 'Unknown')}")
            print()

        print("✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_oauth_flow())
