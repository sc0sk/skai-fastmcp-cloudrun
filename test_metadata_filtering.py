#!/usr/bin/env python3
"""
Test metadata filtering with MCP server.

Tests various filter combinations to verify metadata filtering works correctly:
1. Chamber filter (REPS vs SENATE)
2. Party filter (Liberal, Labor, etc.)
3. Date range filters
4. Combined filters
"""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_chamber_filter():
    """Test chamber filtering - REPS vs SENATE"""
    print("\n" + "="*80)
    print("TEST 1: CHAMBER FILTER")
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

            # Test REPS filter
            print("\n📍 Testing chamber='REPS' filter:")
            result = await session.call_tool(
                "search_hansard_speeches",
                arguments={"query": "policy", "chamber": "REPS", "limit": 3}
            )

            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                print(f"   Found {len(data.get('speeches', []))} speeches")

                for i, speech in enumerate(data.get('speeches', [])[:3], 1):
                    print(f"\n   Speech {i}:")
                    print(f"      speech_id: {speech.get('speech_id')}")
                    print(f"      speaker: {speech.get('speaker')}")
                    print(f"      party: {speech.get('party')}")
                    print(f"      chamber: {speech.get('chamber')} ✓")
                    print(f"      date: {speech.get('date')}")
                    print(f"      similarity: {speech.get('similarity_score', 'N/A')}")

                    # Verify chamber is REPS
                    if speech.get('chamber') != 'REPS':
                        print(f"      ❌ FILTER FAILED: Expected 'REPS', got '{speech.get('chamber')}'")
                    else:
                        print(f"      ✅ FILTER PASSED")


async def test_party_filter():
    """Test party filtering"""
    print("\n" + "="*80)
    print("TEST 2: PARTY FILTER")
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

            # Test Liberal filter
            print("\n📍 Testing party='Liberal' filter:")
            result = await session.call_tool(
                "search_hansard_speeches",
                arguments={"query": "economy", "party": "Liberal", "limit": 3}
            )

            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                print(f"   Found {len(data.get('speeches', []))} speeches")

                for i, speech in enumerate(data.get('speeches', [])[:3], 1):
                    print(f"\n   Speech {i}:")
                    print(f"      speech_id: {speech.get('speech_id')}")
                    print(f"      speaker: {speech.get('speaker')}")
                    print(f"      party: {speech.get('party')} ✓")
                    print(f"      chamber: {speech.get('chamber')}")
                    print(f"      date: {speech.get('date')}")
                    print(f"      similarity: {speech.get('similarity_score', 'N/A')}")

                    # Verify party is Liberal
                    if speech.get('party') != 'Liberal':
                        print(f"      ❌ FILTER FAILED: Expected 'Liberal', got '{speech.get('party')}'")
                    else:
                        print(f"      ✅ FILTER PASSED")


async def test_date_range_filter():
    """Test date range filtering"""
    print("\n" + "="*80)
    print("TEST 3: DATE RANGE FILTER")
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

            # Test date range 2024-06-01 to 2024-06-30
            print("\n📍 Testing date range: 2024-06-01 to 2024-06-30")
            result = await session.call_tool(
                "search_hansard_speeches",
                arguments={
                    "query": "budget",
                    "start_date": "2024-06-01",
                    "end_date": "2024-06-30",
                    "limit": 3
                }
            )

            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                print(f"   Found {len(data.get('speeches', []))} speeches")

                for i, speech in enumerate(data.get('speeches', [])[:3], 1):
                    print(f"\n   Speech {i}:")
                    print(f"      speech_id: {speech.get('speech_id')}")
                    print(f"      speaker: {speech.get('speaker')}")
                    print(f"      party: {speech.get('party')}")
                    print(f"      chamber: {speech.get('chamber')}")
                    print(f"      date: {speech.get('date')} ✓")
                    print(f"      similarity: {speech.get('similarity_score', 'N/A')}")

                    # Verify date is in range
                    speech_date = speech.get('date')
                    if speech_date:
                        if '2024-06-01' <= speech_date <= '2024-06-30':
                            print(f"      ✅ DATE FILTER PASSED")
                        else:
                            print(f"      ❌ DATE FILTER FAILED: Date {speech_date} not in range 2024-06-01 to 2024-06-30")


async def test_combined_filters():
    """Test multiple filters combined"""
    print("\n" + "="*80)
    print("TEST 4: COMBINED FILTERS (chamber + party)")
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

            # Test chamber='REPS' + party='Liberal'
            print("\n📍 Testing chamber='REPS' AND party='Liberal':")
            result = await session.call_tool(
                "search_hansard_speeches",
                arguments={
                    "query": "housing",
                    "chamber": "REPS",
                    "party": "Liberal",
                    "limit": 3
                }
            )

            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                print(f"   Found {len(data.get('speeches', []))} speeches")

                for i, speech in enumerate(data.get('speeches', [])[:3], 1):
                    print(f"\n   Speech {i}:")
                    print(f"      speech_id: {speech.get('speech_id')}")
                    print(f"      speaker: {speech.get('speaker')}")
                    print(f"      party: {speech.get('party')} ✓")
                    print(f"      chamber: {speech.get('chamber')} ✓")
                    print(f"      date: {speech.get('date')}")
                    print(f"      similarity: {speech.get('similarity_score', 'N/A')}")

                    # Verify both filters
                    chamber_ok = speech.get('chamber') == 'REPS'
                    party_ok = speech.get('party') == 'Liberal'

                    if chamber_ok and party_ok:
                        print(f"      ✅ BOTH FILTERS PASSED")
                    else:
                        if not chamber_ok:
                            print(f"      ❌ CHAMBER FILTER FAILED: Expected 'REPS', got '{speech.get('chamber')}'")
                        if not party_ok:
                            print(f"      ❌ PARTY FILTER FAILED: Expected 'Liberal', got '{speech.get('party')}'")


async def main():
    """Run all metadata filtering tests"""
    print("\n" + "="*80)
    print("MCP METADATA FILTERING TESTS")
    print("="*80)
    print("\nTesting all metadata filter combinations:")

    try:
        await test_chamber_filter()
        await test_party_filter()
        await test_date_range_filter()
        await test_combined_filters()

        print("\n" + "="*80)
        print("✅ ALL METADATA FILTERING TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
