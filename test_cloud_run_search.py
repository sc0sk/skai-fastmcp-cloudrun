"""Test Cloud Run MCP server end-to-end with search_hansard_speeches tool."""
import asyncio
import httpx
import json

async def test_search():
    """Test the search tool via HTTP."""
    url = "https://hansard-mcp-server-666924716777.us-central1.run.app"
    
    # Try different possible endpoints
    endpoints = ["/", "/sse", "/mcp", "/mcp/sse", "/messages"]
    
    for endpoint in endpoints:
        try:
            print(f"\n🔍 Trying {url}{endpoint}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try both GET and POST
                try:
                    response = await client.get(f"{url}{endpoint}")
                    if response.status_code != 404:
                        print(f"  GET {endpoint}: {response.status_code}")
                        print(f"  Response: {response.text[:200]}")
                except Exception as e:
                    print(f"  GET error: {e}")
                
                # Try JSON-RPC POST
                try:
                    json_rpc = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list"
                    }
                    response = await client.post(
                        f"{url}{endpoint}",
                        json=json_rpc,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code != 404:
                        print(f"  POST {endpoint}: {response.status_code}")
                        print(f"  Response: {response.text[:500]}")
                except Exception as e:
                    print(f"  POST error: {e}")
                    
        except Exception as e:
            print(f"  Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
