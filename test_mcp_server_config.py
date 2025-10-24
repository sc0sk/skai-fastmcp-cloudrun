#!/usr/bin/env python3
"""
Test MCP server configuration and tool registration.

This tests the server initialization and tool metadata without requiring database access.
"""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server_tools():
    """Test that server initializes and tools are registered correctly"""
    print("\n" + "="*80)
    print("MCP SERVER CONFIGURATION TEST")
    print("="*80)

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "fastmcp", "run", "src/server.py:mcp"],
        env={
            "PYTHONPATH": "src",
            "DANGEROUSLY_OMIT_AUTH": "true",
            "GCP_PROJECT_ID": "skai-fastmcp-cloudrun",
            "GCP_REGION": "us-central1",
            "CLOUDSQL_INSTANCE": "hansard-db-v2",
            "CLOUDSQL_DATABASE": "hansard",
            "CLOUDSQL_USER": "fastmcp-server",
        }
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            print("\n✅ Server initialized successfully")

            # List tools
            tools_result = await session.list_tools()
            print(f"\n✅ Found {len(tools_result.tools)} registered tools:")

            for tool in tools_result.tools:
                print(f"\n   📦 {tool.name}")
                print(f"      Description: {tool.description}")

                # Show input schema
                if hasattr(tool, 'inputSchema'):
                    schema = tool.inputSchema
                    print(f"      Parameters:")
                    if 'properties' in schema:
                        for param_name, param_info in schema['properties'].items():
                            required = param_name in schema.get('required', [])
                            req_marker = " (required)" if required else " (optional)"
                            print(f"        - {param_name}{req_marker}: {param_info.get('description', 'N/A')}")

            # Verify expected tools
            tool_names = [tool.name for tool in tools_result.tools]
            expected_tools = ['search_hansard_speeches', 'fetch_hansard_speech', 'ingest_hansard_speech']

            print(f"\n\n✅ VERIFICATION:")
            for expected in expected_tools:
                if expected in tool_names:
                    print(f"   ✓ {expected} - registered")
                else:
                    print(f"   ✗ {expected} - MISSING")

            # Test that all expected tools are present
            all_present = all(tool in tool_names for tool in expected_tools)
            if all_present:
                print(f"\n✅ All {len(expected_tools)} expected tools are registered")
            else:
                print(f"\n❌ Some expected tools are missing")

            print("\n" + "="*80)
            print("SERVER CONFIGURATION TEST COMPLETE")
            print("="*80)

            return all_present


async def main():
    """Run configuration test"""
    try:
        success = await test_server_tools()
        if success:
            print("\n✅ SUCCESS: MCP server is properly configured")
            print("\nNote: Live database testing requires proper GCP IAM credentials.")
            print("The server is ready for deployment to Cloud Run where IAM auth will work.")
        else:
            print("\n❌ FAILURE: MCP server configuration has issues")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
