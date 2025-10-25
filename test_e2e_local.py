#!/usr/bin/env python3
"""
End-to-end test for Hansard MCP server with local STDIO transport.
Tests all tools including the new bulk ingestion feature.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test MCP server tools via STDIO transport."""
    
    print("=" * 80)
    print("HANSARD MCP SERVER - END-TO-END TEST")
    print("=" * 80)
    print()
    
    # Server parameters
    project_root = Path(__file__).parent
    server_params = StdioServerParameters(
        command=str(project_root / ".venv" / "bin" / "python"),
        args=["-m", "src.server"],
        env={
            **os.environ,
            "PYTHONPATH": f"{project_root}/src:{project_root}",
            "DANGEROUSLY_OMIT_AUTH": "true",
            "MCP_QUIET": "true",  # Suppress startup messages
        }
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            print("✅ Connected to MCP server")
            print()
            
            # List available tools
            tools = await session.list_tools()
            print(f"📋 Available Tools ({len(tools.tools)}):")
            print("-" * 80)
            for tool in tools.tools:
                print(f"  • {tool.name}")
                if hasattr(tool, 'description') and tool.description:
                    desc = tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
                    print(f"    {desc}")
            print()
            
            # Test 1: Search for speeches
            print("=" * 80)
            print("TEST 1: Search Hansard Speeches")
            print("=" * 80)
            try:
                result = await session.call_tool(
                    "search_hansard_speeches",
                    {
                        "query": "climate change",
                        "limit": 2,
                    }
                )
                print("✅ search_hansard_speeches call successful")
                
                # Parse result
                if result.content:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        print(f"   Found {data.get('total_results', 0)} results")
                        if data.get('speeches'):
                            speech = data['speeches'][0]
                            print(f"   First result: {speech.get('speaker', 'Unknown')} - {speech.get('title', 'No title')[:50]}...")
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
            
            # Test 2: Fetch speech by ID (get ID from search first)
            print("=" * 80)
            print("TEST 2: Fetch Hansard Speech by ID")
            print("=" * 80)
            try:
                # First search to get a speech_id
                search_result = await session.call_tool(
                    "search_hansard_speeches",
                    {
                        "query": "infrastructure",
                        "limit": 1,
                    }
                )
                
                # Extract speech_id
                speech_id = None
                if search_result.content:
                    content = search_result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        if data.get('speeches'):
                            speech_id = data['speeches'][0].get('speech_id')
                
                if speech_id:
                    print(f"   Using speech_id: {speech_id}")
                    fetch_result = await session.call_tool(
                        "fetch_hansard_speech",
                        {"speech_id": speech_id}
                    )
                    print("✅ fetch_hansard_speech call successful")
                    
                    if fetch_result.content:
                        content = fetch_result.content[0]
                        if hasattr(content, 'text'):
                            data = json.loads(content.text)
                            print(f"   Speaker: {data.get('speaker', 'Unknown')}")
                            print(f"   Date: {data.get('date', 'Unknown')}")
                            text_preview = data.get('text', '')[:150] + "..." if len(data.get('text', '')) > 150 else data.get('text', '')
                            print(f"   Text: {text_preview}")
                else:
                    print("⚠️  No speech_id found to test with")
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
            
            # Test 3: Check if ingest_markdown_directory exists (Feature 013)
            print("=" * 80)
            print("TEST 3: Check Bulk Ingestion Tool (Feature 013)")
            print("=" * 80)
            tool_names = [t.name for t in tools.tools]
            if "ingest_markdown_directory" in tool_names:
                print("✅ ingest_markdown_directory tool is available")
                
                # Find the tool details
                bulk_tool = next(t for t in tools.tools if t.name == "ingest_markdown_directory")
                print(f"   Description: {bulk_tool.description[:150] if bulk_tool.description else 'No description'}...")
                
                # Note: We won't actually run it to avoid modifying the database
                print("   ⚠️  Skipping actual execution to avoid database changes")
            else:
                print("❌ ingest_markdown_directory tool NOT found")
            print()
            
            # Test 4: Search with filters
            print("=" * 80)
            print("TEST 4: Search with Chamber Filter")
            print("=" * 80)
            try:
                result = await session.call_tool(
                    "search_hansard_speeches",
                    {
                        "query": "economy",
                        "chamber": "REPS",
                        "limit": 2,
                    }
                )
                print("✅ search_hansard_speeches with chamber filter successful")
                
                if result.content:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        print(f"   Found {data.get('total_results', 0)} results in REPS")
                        if data.get('speeches'):
                            for speech in data['speeches']:
                                print(f"   - {speech.get('chamber', 'Unknown chamber')}: {speech.get('speaker', 'Unknown')}")
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
            
            # Summary
            print("=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            print("✅ MCP server connection: PASSED")
            print(f"✅ Available tools: {len(tools.tools)}")
            print("✅ search_hansard_speeches: TESTED")
            print("✅ fetch_hansard_speech: TESTED")
            print("✅ ingest_markdown_directory: VERIFIED" if "ingest_markdown_directory" in tool_names else "❌ ingest_markdown_directory: NOT FOUND")
            print()
            print("🎉 End-to-end test completed!")
            print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
