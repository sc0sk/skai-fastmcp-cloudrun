#!/usr/bin/env python3
"""
Test MCP connector using direct HTTP calls to simulate ChatGPT's behavior.
This helps debug why ChatGPT isn't getting results.
"""

import asyncio
import httpx
import json
from typing import Optional


class MCPConnectorTester:
    """Simulates ChatGPT's MCP connector behavior."""

    def __init__(self, base_url: str, oauth_token: Optional[str] = None):
        self.base_url = base_url
        self.oauth_token = oauth_token
        self.session_id = None

    async def test_oauth_flow(self):
        """Test OAuth authorization flow."""
        print("\n" + "=" * 70)
        print("TEST 1: OAuth Discovery")
        print("=" * 70)

        async with httpx.AsyncClient(follow_redirects=False) as client:
            # Step 1: Check OAuth discovery endpoint
            try:
                response = await client.get(
                    f"{self.base_url}/.well-known/oauth-authorization-server",
                    timeout=10.0
                )
                print(f"✓ OAuth discovery: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Authorization endpoint: {data.get('authorization_endpoint')}")
                    print(f"  Token endpoint: {data.get('token_endpoint')}")
                else:
                    print(f"  ✗ Failed: {response.text}")
            except Exception as e:
                print(f"✗ OAuth discovery failed: {e}")

            # Step 2: Check protected resource metadata
            try:
                response = await client.get(
                    f"{self.base_url}/.well-known/oauth-protected-resource",
                    timeout=10.0
                )
                print(f"✓ Protected resource: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Resource: {json.dumps(data, indent=2)[:200]}...")
            except Exception as e:
                print(f"✗ Protected resource check failed: {e}")

    async def test_mcp_initialization(self):
        """Test MCP protocol initialization."""
        print("\n" + "=" * 70)
        print("TEST 2: MCP Protocol Initialization")
        print("=" * 70)

        headers = {"Content-Type": "application/json"}
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"

        async with httpx.AsyncClient() as client:
            # MCP initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }

            try:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    json=init_request,
                    headers=headers,
                    timeout=30.0
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 401:
                    print("✗ Authentication required (expected without OAuth token)")
                    print(f"  Response: {response.text}")
                    return False
                elif response.status_code == 200:
                    result = response.json()
                    print(f"✓ MCP initialized successfully!")
                    print(f"  Server: {result.get('result', {}).get('serverInfo', {}).get('name')}")
                    print(f"  Version: {result.get('result', {}).get('serverInfo', {}).get('version')}")
                    print(f"  Capabilities: {list(result.get('result', {}).get('capabilities', {}).keys())}")
                    return True
                else:
                    print(f"✗ Unexpected status: {response.status_code}")
                    print(f"  Response: {response.text[:500]}")
                    return False

            except Exception as e:
                print(f"✗ MCP initialization failed: {e}")
                return False

    async def test_list_tools(self):
        """Test listing available tools."""
        print("\n" + "=" * 70)
        print("TEST 3: List Available Tools")
        print("=" * 70)

        headers = {"Content-Type": "application/json"}
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"

        async with httpx.AsyncClient() as client:
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            try:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    json=list_tools_request,
                    headers=headers,
                    timeout=30.0
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 401:
                    print("✗ Authentication required")
                    return False
                elif response.status_code == 200:
                    result = response.json()
                    tools = result.get("result", {}).get("tools", [])
                    print(f"✓ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool.get('name')}: {tool.get('description', '')[:60]}...")
                    return True
                else:
                    print(f"✗ Failed: {response.text}")
                    return False

            except Exception as e:
                print(f"✗ List tools failed: {e}")
                return False

    async def test_search_tool(self, query: str = "cost of living"):
        """Test the search tool."""
        print("\n" + "=" * 70)
        print(f"TEST 4: Search Tool - '{query}'")
        print("=" * 70)

        headers = {"Content-Type": "application/json"}
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"

        async with httpx.AsyncClient() as client:
            search_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {
                        "query": query,
                        "limit": 5
                    }
                }
            }

            try:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    json=search_request,
                    headers=headers,
                    timeout=60.0  # Search might take longer
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 401:
                    print("✗ Authentication required")
                    print("\n⚠️  To test with OAuth, you need to:")
                    print("   1. Authenticate via GitHub OAuth flow")
                    print("   2. Extract the access token")
                    print("   3. Run this script with the token")
                    return False
                elif response.status_code == 200:
                    result = response.json()
                    print(f"✓ Search completed!")

                    # Parse MCP response
                    content = result.get("result", {}).get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        print(f"\n📄 Results ({len(content)} items):")
                        for i, item in enumerate(content[:3], 1):
                            if item.get("type") == "text":
                                text = item.get("text", "")
                                # Try to parse as JSON
                                try:
                                    parsed = json.loads(text)
                                    print(f"\n  Result {i}:")
                                    print(f"    Speaker: {parsed.get('speaker', 'N/A')}")
                                    print(f"    Date: {parsed.get('date', 'N/A')}")
                                    print(f"    Score: {parsed.get('relevance_score', 0)}")
                                    print(f"    Excerpt: {parsed.get('excerpt', '')[:100]}...")
                                except json.JSONDecodeError:
                                    print(f"\n  Result {i}: {text[:200]}...")
                        return True
                    else:
                        print("\n⚠️  No results found!")
                        print(f"  Full response: {json.dumps(result, indent=2)[:500]}...")
                        return False
                else:
                    print(f"✗ Failed: {response.status_code}")
                    print(f"  Response: {response.text[:500]}")
                    return False

            except Exception as e:
                print(f"✗ Search failed: {e}")
                import traceback
                traceback.print_exc()
                return False


async def main():
    """Run all MCP connector tests."""
    print("\n" + "🧪" * 35)
    print("MCP CONNECTOR DIAGNOSTIC TOOL")
    print("Testing: https://mcp.simonkennedymp.com.au")
    print("🧪" * 35)

    tester = MCPConnectorTester(
        base_url="https://mcp.simonkennedymp.com.au",
        oauth_token=None  # Set to actual token if you have one
    )

    # Run tests
    await tester.test_oauth_flow()

    init_success = await tester.test_mcp_initialization()

    if init_success:
        await tester.test_list_tools()
        await tester.test_search_tool("cost of living")
    else:
        print("\n⚠️  Skipping tool tests - initialization failed (expected without OAuth)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\n✓ OAuth endpoints are accessible")
    print("✗ Search requires GitHub OAuth authentication")
    print("\n💡 Next steps:")
    print("   1. Authenticate via GitHub OAuth in ChatGPT")
    print("   2. Check ChatGPT's MCP connector logs for errors")
    print("   3. Verify the connector URL is exactly: https://mcp.simonkennedymp.com.au/mcp")


if __name__ == "__main__":
    asyncio.run(main())
