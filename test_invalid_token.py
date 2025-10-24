#!/usr/bin/env python3
"""Test invalid token rejection"""
import asyncio
import httpx


async def test_invalid_token():
    """Test that invalid tokens are rejected"""
    url = "http://localhost:8000/mcp/"

    # Test cases
    test_cases = [
        ("invalid-token", "Invalid token"),
        ("guest-token-abcde", "Guest token (no scopes)"),
        (None, "No token"),
    ]

    for token, description in test_cases:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }

        async with httpx.AsyncClient() as client:
            print(f"\nTesting: {description}")
            print(f"Token: {token or 'None'}")
            response = await client.post(url, json=request, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")


if __name__ == "__main__":
    asyncio.run(test_invalid_token())
