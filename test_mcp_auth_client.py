#!/usr/bin/env python3
"""
Test client for MCP server with bearer token authentication.
"""
import asyncio
import httpx


async def test_mcp_tools_list():
    """Test the tools/list endpoint with bearer token"""
    url = "http://localhost:8000/mcp/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer admin-token-12345",
    }

    # Initialize request - this is the first message in MCP protocol
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        print("Sending initialize request...")
        response = await client.post(url, json=init_request, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")

        if response.status_code == 200:
            # Now request tools/list
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            print("Sending tools/list request...")
            response = await client.post(url, json=tools_request, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")


if __name__ == "__main__":
    asyncio.run(test_mcp_tools_list())
