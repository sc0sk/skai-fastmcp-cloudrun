#!/usr/bin/env python3
"""
Test MCP server tools with live Cloud SQL data.

Tests all three tools:
1. search_hansard_speeches - semantic search
2. fetch_hansard_speech - fetch by ID
3. ingest_hansard_speech - add new speech

This uses the MCP Client SDK to connect to the running server.
"""
import asyncio
import json
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_search():
    """Test search_hansard_speeches tool"""
    print("\n" + "="*80)
    print("TEST 1: search_hansard_speeches")
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
            await session.initialize()

            # Test search
            result = await session.call_tool(
                "search_hansard_speeches",
                arguments={
                    "query": "climate change policy",
                    "limit": 3
                }
            )

            print(f"\n✅ Search Results:")
            print(f"   Query: 'climate change policy'")
            print(f"   Limit: 3")

            # Parse result
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        data = json.loads(item.text)
                        print(f"\n   Found {len(data.get('speeches', []))} speeches:")
                        for i, speech in enumerate(data.get('speeches', [])[:3], 1):
                            print(f"     {i}. {speech.get('speaker')} ({speech.get('party')})")
                            print(f"        Date: {speech.get('date')}")
                            print(f"        Chamber: {speech.get('chamber')}")
                            print(f"        Similarity: {speech.get('similarity_score', 'N/A')}")
                            if 'speech_id' in speech:
                                print(f"        Speech ID: {speech['speech_id']}")


async def test_fetch():
    """Test fetch_hansard_speech tool"""
    print("\n" + "="*80)
    print("TEST 2: fetch_hansard_speech")
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
            await session.initialize()

            # First get a speech ID from search
            search_result = await session.call_tool(
                "search_hansard_speeches",
                arguments={"query": "budget", "limit": 1}
            )

            speech_id = None
            if search_result.content:
                for item in search_result.content:
                    if hasattr(item, 'text'):
                        data = json.loads(item.text)
                        speeches = data.get('speeches', [])
                        if speeches:
                            speech_id = speeches[0].get('speech_id')

            if not speech_id:
                print("   ❌ Could not find a speech ID to test with")
                return

            # Fetch the speech
            result = await session.call_tool(
                "fetch_hansard_speech",
                arguments={"speech_id": speech_id}
            )

            print(f"\n✅ Fetch Results:")
            print(f"   Speech ID: {speech_id}")

            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        data = json.loads(item.text)
                        print(f"\n   Speaker: {data.get('speaker')}")
                        print(f"   Party: {data.get('party')}")
                        print(f"   Date: {data.get('date')}")
                        print(f"   Chamber: {data.get('chamber')}")
                        print(f"   Text length: {len(data.get('text', ''))} characters")
                        print(f"   Text preview: {data.get('text', '')[:200]}...")


async def test_ingest():
    """Test ingest_hansard_speech tool"""
    print("\n" + "="*80)
    print("TEST 3: ingest_hansard_speech")
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
            await session.initialize()

            # Create test speech
            test_speech = {
                "speech_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "speaker": "Test Speaker",
                "party": "ALP",
                "chamber": "REPS",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "text": "This is a test speech about important policy matters. It demonstrates the ingest functionality of the MCP server.",
            }

            print(f"\n   Ingesting test speech:")
            print(f"   Speech ID: {test_speech['speech_id']}")
            print(f"   Speaker: {test_speech['speaker']}")
            print(f"   Party: {test_speech['party']}")

            result = await session.call_tool(
                "ingest_hansard_speech",
                arguments=test_speech
            )

            print(f"\n✅ Ingest Results:")
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        data = json.loads(item.text)
                        print(f"   Status: {data.get('status')}")
                        print(f"   Message: {data.get('message')}")
                        print(f"   Speech ID: {data.get('speech_id')}")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MCP LIVE TESTING WITH CLOUD SQL")
    print("="*80)
    print("\nTesting all three MCP tools with live data:")
    print("1. search_hansard_speeches")
    print("2. fetch_hansard_speech")
    print("3. ingest_hansard_speech")

    try:
        await test_search()
        await test_fetch()
        await test_ingest()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
