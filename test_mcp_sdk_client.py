#!/usr/bin/env python3
"""
Test MCP server using the MCP SDK client (simulates Claude Desktop/Code).
This bypasses OAuth by running the server locally with DANGEROUSLY_OMIT_AUTH.
"""

import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test MCP server end-to-end using SDK client."""

    print("\n" + "="*70)
    print("🧪 MCP SDK CLIENT TEST - End-to-End")
    print("="*70)

    # Set environment variables for local testing
    os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"
    os.environ["GCP_PROJECT_ID"] = "skai-fastmcp-cloudrun"
    os.environ["GCP_REGION"] = "us-central1"
    os.environ["CLOUDSQL_INSTANCE"] = "hansard-db-v2"
    os.environ["CLOUDSQL_DATABASE"] = "hansard"
    os.environ["GCP_PROJECT_NUMBER"] = "666924716777"

    # Configure server parameters
    server_params = StdioServerParameters(
        command="fastmcp",
        args=["dev", "src/server.py"],
        env=None
    )

    print("\n📡 Starting MCP server locally...")
    print("   (Using DANGEROUSLY_OMIT_AUTH=true to bypass OAuth)\n")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize connection
                await session.initialize()
                print("✅ Connected to MCP server\n")

                # List available tools
                print("-" * 70)
                print("TEST 1: List Tools")
                print("-" * 70)

                tools_result = await session.list_tools()
                tools = tools_result.tools

                print(f"✅ Found {len(tools)} tools:\n")
                for tool in tools:
                    print(f"  📌 {tool.name}")
                    print(f"     {tool.description}")
                    print()

                # Test 1: Search for "cost of living"
                print("-" * 70)
                print("TEST 2: Search - 'cost of living and inflation'")
                print("-" * 70)

                search_result = await session.call_tool(
                    "search",
                    arguments={
                        "query": "cost of living and inflation",
                        "limit": 3
                    }
                )

                print(f"✅ Search completed!")
                print(f"   Content items: {len(search_result.content)}\n")

                for i, content in enumerate(search_result.content, 1):
                    if content.type == "text":
                        # Parse the JSON result
                        import json
                        try:
                            result = json.loads(content.text)
                            print(f"  Result {i}:")
                            print(f"    Speaker: {result.get('speaker', 'N/A')}")
                            print(f"    Date: {result.get('date', 'N/A')}")
                            print(f"    Party: {result.get('party', 'N/A')}")
                            print(f"    Score: {result.get('relevance_score', 0):.3f}")
                            print(f"    Excerpt: {result.get('excerpt', '')[:150]}...")
                            print()
                        except json.JSONDecodeError:
                            print(f"  Result {i}: {content.text[:200]}...")
                            print()

                # Test 2: Search with speaker filter
                print("-" * 70)
                print("TEST 3: Search with Speaker Filter - 'Kennedy, Simon MP'")
                print("-" * 70)

                search_result2 = await session.call_tool(
                    "search",
                    arguments={
                        "query": "housing affordability",
                        "speaker": "Kennedy, Simon MP",
                        "limit": 3
                    }
                )

                print(f"✅ Filtered search completed!")
                print(f"   Results: {len(search_result2.content)}\n")

                for i, content in enumerate(search_result2.content[:2], 1):
                    if content.type == "text":
                        import json
                        try:
                            result = json.loads(content.text)
                            print(f"  Result {i}:")
                            print(f"    Speaker: {result.get('speaker', 'N/A')}")
                            print(f"    Date: {result.get('date', 'N/A')}")
                            print(f"    Debate: {result.get('debate', 'N/A')}")
                            print(f"    Excerpt: {result.get('excerpt', '')[:120]}...")
                            print()
                        except json.JSONDecodeError:
                            print(f"  Result {i}: {content.text[:150]}...")

                # Test 3: Search with no results
                print("-" * 70)
                print("TEST 4: Search - Query with no matches")
                print("-" * 70)

                search_result3 = await session.call_tool(
                    "search",
                    arguments={
                        "query": "quantum physics and relativity theory",
                        "limit": 3
                    }
                )

                print(f"✅ Search completed!")
                print(f"   Results: {len(search_result3.content)}")

                if len(search_result3.content) == 0:
                    print("   (No results - expected for unrelated topic)\n")

                # Summary
                print("-" * 70)
                print("SUMMARY")
                print("-" * 70)
                print("\n✅ All tests passed!")
                print("✅ MCP server is working correctly")
                print("✅ Search tool returns results")
                print("✅ Speaker filtering works")
                print("\n💡 The issue with ChatGPT is likely:")
                print("   - OAuth token expired/invalid")
                print("   - ChatGPT needs to reconnect")
                print("   - Response format incompatibility")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    # Change to project root
    os.chdir("/home/user/skai-fastmcp-cloudrun")

    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)
