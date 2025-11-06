#!/usr/bin/env python3
"""Automated MCP tests for Hansard server."""
import asyncio
import json
import subprocess

async def get_token():
    """Get auth token."""
    result = subprocess.run(["gcloud", "auth", "print-identity-token"], capture_output=True, text=True, check=True)
    return result.stdout.strip()

async def test_debug():
    """Test debug endpoint."""
    import httpx
    print("\n=== TEST: Debug IAM Detection ===")
    token = await get_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://hansard-mcp-server-666924716777.us-central1.run.app/debug/iam-user",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
            return True
        print(f"Error: {response.text}")
        return False

async def main():
    """Run tests."""
    print("=== MCP INSPECTOR TESTS ===")
    result = await test_debug()
    print(f"\n{'✅ PASS' if result else '❌ FAIL'}")
    return result

if __name__ == "__main__":
    asyncio.run(main())
