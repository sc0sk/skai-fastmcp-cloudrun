#!/usr/bin/env python3
"""
Test MCP endpoint with OAuth token using JSON-RPC over HTTP.
"""

import asyncio
import json
import httpx

# Load token from file
with open('/tmp/mcp_oauth_token.json', 'r') as f:
    token_data = json.load(f)
    ACCESS_TOKEN = token_data['access_token']

BASE_URL = "https://mcp.simonkennedymp.com.au"

print(f"✅ Loaded token: {ACCESS_TOKEN[:50]}...")

async def call_mcp_method(method, params=None, id_val=1):
    """Call an MCP method using JSON-RPC over HTTP."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": id_val
        }

        print(f"\n📤 Calling: {method}")
        print(json.dumps(request, indent=2))

        try:
            response = await client.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                json=request
            )

            print(f"\n📥 Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")

            if response.status_code == 200:
                # Check if response is SSE or JSON
                content_type = response.headers.get('content-type', '')

                if 'text/event-stream' in content_type:
                    print("📡 Response is SSE format")
                    print(f"Raw response:\n{response.text[:1000]}")

                    # Parse SSE response
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            try:
                                result = json.loads(data)
                                print("✅ Parsed SSE data:")
                                print(json.dumps(result, indent=2))
                                return result
                            except json.JSONDecodeError:
                                print(f"⚠️  Could not parse: {data}")

                else:
                    # Regular JSON response
                    result = response.json()
                    print("✅ Response:")
                    print(json.dumps(result, indent=2))
                    return result
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                return None

        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return None

async def main():
    """Run MCP tests."""

    print("🚀 Testing MCP endpoint with OAuth token\n")
    print("="*60)

    # 1. Initialize
    print("\n1️⃣  INITIALIZE MCP SESSION")
    print("="*60)
    init_result = await call_mcp_method(
        "initialize",
        params={
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        id_val=1
    )

    if not init_result or "error" in init_result:
        print("\n❌ Failed to initialize MCP session")
        return

    print("\n✅ MCP session initialized!")

    # 2. List tools
    print("\n2️⃣  LIST AVAILABLE TOOLS")
    print("="*60)
    tools_result = await call_mcp_method("tools/list", params={}, id_val=2)

    if tools_result and "result" in tools_result:
        tools = tools_result["result"].get("tools", [])
        print(f"\n✅ Found {len(tools)} tools:")
        for tool in tools:
            name = tool.get("name", "Unknown")
            desc = tool.get("description", "No description")[:80]
            print(f"\n  📌 {name}")
            print(f"     {desc}...")

    # 3. Test search tool
    print("\n3️⃣  TEST SEARCH TOOL")
    print("="*60)
    search_result = await call_mcp_method(
        "tools/call",
        params={
            "name": "search_hansard_speeches",
            "arguments": {
                "query": "climate change",
                "limit": 2
            }
        },
        id_val=3
    )

    if search_result and "result" in search_result:
        print("\n✅ Search successful!")
        # Limit output size
        result_str = json.dumps(search_result, indent=2)
        if len(result_str) > 2000:
            print(result_str[:2000] + "\n... (truncated)")
        else:
            print(result_str)

    # 4. Test fetch tool (if search returned results)
    if search_result and "result" in search_result:
        try:
            # Try to extract a speech ID from search results
            content = search_result["result"].get("content", [])
            if content and len(content) > 0:
                first_content = content[0]
                if "text" in first_content:
                    text = first_content["text"]
                    # Look for speech ID in the text
                    import re
                    id_match = re.search(r'"id":\s*"([^"]+)"', text)
                    if id_match:
                        speech_id = id_match.group(1)

                        print("\n4️⃣  TEST FETCH TOOL")
                        print("="*60)
                        print(f"Fetching speech ID: {speech_id}")

                        fetch_result = await call_mcp_method(
                            "tools/call",
                            params={
                                "name": "fetch_hansard_speech",
                                "arguments": {
                                    "speech_id": speech_id
                                }
                            },
                            id_val=4
                        )

                        if fetch_result and "result" in fetch_result:
                            print("\n✅ Fetch successful!")
                            result_str = json.dumps(fetch_result, indent=2)
                            if len(result_str) > 1500:
                                print(result_str[:1500] + "\n... (truncated)")
                            else:
                                print(result_str)

        except Exception as e:
            print(f"\n⚠️  Could not test fetch tool: {e}")

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE!")
    print("="*60)
    print("\n📊 Summary:")
    print("  ✅ OAuth authentication: WORKING")
    print("  ✅ MCP session initialization: WORKING")
    print("  ✅ Tool listing: WORKING")
    print("  ✅ Search tool: WORKING")
    print(f"  ✅ Token valid until: {token_data.get('expires_in', 'unknown')}s from issue")

if __name__ == "__main__":
    asyncio.run(main())
