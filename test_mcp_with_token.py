#!/usr/bin/env python3
"""
Test MCP endpoint with OAuth token using MCP protocol.
"""

import asyncio
import json
import httpx
from httpx_sse import aconnect_sse

# Load token from file
with open('/tmp/mcp_oauth_token.json', 'r') as f:
    token_data = json.load(f)
    ACCESS_TOKEN = token_data['access_token']

BASE_URL = "https://mcp.simonkennedymp.com.au"

print(f"✅ Loaded token: {ACCESS_TOKEN[:50]}...")

async def test_mcp_sse():
    """Test MCP endpoint using SSE (Server-Sent Events)."""

    print("\n🧪 Testing MCP endpoint with SSE...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json"
        }

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }

        print(f"\n📤 Sending initialize request...")
        print(json.dumps(init_request, indent=2))

        try:
            async with aconnect_sse(
                client, "POST", f"{BASE_URL}/mcp", headers=headers, json=init_request
            ) as event_source:
                print("\n📥 Receiving events...")
                async for sse in event_source.aiter_sse():
                    print(f"\n🔔 Event: {sse.event}")
                    print(f"Data: {sse.data}")

                    # Parse the response
                    try:
                        response = json.loads(sse.data)
                        print("\n✅ Parsed response:")
                        print(json.dumps(response, indent=2))

                        # If initialization successful, list tools
                        if response.get("result"):
                            print("\n✅ MCP initialized successfully!")
                            await list_tools(client, headers)
                            break

                    except json.JSONDecodeError as e:
                        print(f"⚠️  Could not parse JSON: {e}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

async def list_tools(client, headers):
    """List available MCP tools."""

    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }

    print(f"\n📤 Sending tools/list request...")
    print(json.dumps(list_tools_request, indent=2))

    try:
        async with aconnect_sse(
            client, "POST", f"{BASE_URL}/mcp", headers=headers, json=list_tools_request
        ) as event_source:
            print("\n📥 Receiving tools list...")
            async for sse in event_source.aiter_sse():
                try:
                    response = json.loads(sse.data)
                    print("\n✅ Available tools:")
                    print(json.dumps(response, indent=2))

                    if response.get("result") and "tools" in response["result"]:
                        tools = response["result"]["tools"]
                        print(f"\n📋 Found {len(tools)} tools:")
                        for tool in tools:
                            print(f"  - {tool.get('name')}: {tool.get('description', 'No description')[:100]}")

                        # Test search tool
                        if any(t['name'] == 'search_hansard_speeches' for t in tools):
                            await test_search_tool(client, headers)

                    break

                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse JSON: {e}")

    except Exception as e:
        print(f"❌ Error listing tools: {e}")
        import traceback
        traceback.print_exc()

async def test_search_tool(client, headers):
    """Test the search_hansard_speeches tool."""

    search_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_hansard_speeches",
            "arguments": {
                "query": "climate change",
                "limit": 3
            }
        },
        "id": 3
    }

    print(f"\n📤 Testing search tool: search_hansard_speeches")
    print(json.dumps(search_request, indent=2))

    try:
        async with aconnect_sse(
            client, "POST", f"{BASE_URL}/mcp", headers=headers, json=search_request
        ) as event_source:
            print("\n📥 Receiving search results...")
            async for sse in event_source.aiter_sse():
                try:
                    response = json.loads(sse.data)
                    print("\n✅ Search results:")
                    print(json.dumps(response, indent=2)[:2000])  # Limit output
                    break

                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse JSON: {e}")

    except Exception as e:
        print(f"❌ Error calling search tool: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing MCP endpoint with OAuth token\n")
    asyncio.run(test_mcp_sse())
    print("\n✅ Testing complete!")
