#!/usr/bin/env python3
"""End-to-end test script for Hansard MCP tools via Claude Code CLI."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tools.search import search_hansard_speeches
from tools.fetch import fetch_hansard_speech

async def test_climate_search():
    """Test 1: Search for climate change policy speeches."""
    print("\n=== Test 1: Climate Change Policy Search ===")
    try:
        result = await search_hansard_speeches(
            query="climate change carbon emissions renewable energy",
            limit=5
        )
        print(f"✓ Search completed: {result['total_results']} results")
        for i, speech in enumerate(result['speeches'][:3], 1):
            print(f"  {i}. {speech['speaker_name']} - {speech['date']}")
            print(f"     Relevance: {speech['relevance_score']:.3f}")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

async def test_healthcare_search():
    """Test 2: Search for healthcare reform debates."""
    print("\n=== Test 2: Healthcare Reform Search ===")
    try:
        result = await search_hansard_speeches(
            query="healthcare reform medicare hospitals medical services",
            limit=5
        )
        print(f"✓ Search completed: {result['total_results']} results")
        for i, speech in enumerate(result['speeches'][:3], 1):
            print(f"  {i}. {speech['speaker_name']} - {speech['date']}")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

async def test_party_filter():
    """Test 3: Filter speeches by party."""
    print("\n=== Test 3: Party-Based Filtering ===")
    try:
        # Test Labor party filter
        result_labor = await search_hansard_speeches(
            query="economic policy",
            party="ALP",
            limit=3
        )
        print(f"✓ Labor speeches: {result_labor['total_results']} results")

        # Test Liberal party filter
        result_liberal = await search_hansard_speeches(
            query="economic policy",
            party="LP",
            limit=3
        )
        print(f"✓ Liberal speeches: {result_liberal['total_results']} results")
        return True
    except Exception as e:
        print(f"✗ Party filter failed: {e}")
        return False

async def test_budget_search():
    """Test 4: Search for budget-related speeches."""
    print("\n=== Test 4: Budget Policy Search ===")
    try:
        result = await search_hansard_speeches(
            query="federal budget taxation spending fiscal policy",
            limit=5
        )
        print(f"✓ Search completed: {result['total_results']} results")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

async def test_fetch_speech():
    """Test 5: Fetch full speech by ID."""
    print("\n=== Test 5: Fetch Speech by ID ===")
    try:
        # First search to get a speech ID
        search_result = await search_hansard_speeches(
            query="parliament",
            limit=1
        )
        if search_result['total_results'] > 0:
            speech_id = search_result['speeches'][0]['speech_id']
            print(f"  Found speech ID: {speech_id}")

            # Fetch the full speech
            full_speech = await fetch_hansard_speech(speech_id=speech_id)
            print(f"✓ Fetched speech by {full_speech['speaker_name']}")
            print(f"  Date: {full_speech['date']}")
            print(f"  Text length: {len(full_speech['full_text'])} chars")
            return True
        else:
            print("✗ No speeches found to fetch")
            return False
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        return False

async def test_date_range():
    """Test 6: Search with date range filtering."""
    print("\n=== Test 6: Date Range Filtering ===")
    try:
        result = await search_hansard_speeches(
            query="policy",
            start_date="2020-01-01",
            end_date="2023-12-31",
            limit=5
        )
        print(f"✓ Search with date range: {result['total_results']} results")
        return True
    except Exception as e:
        print(f"✗ Date range search failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Hansard MCP End-to-End Tests")
    print("=" * 60)

    tests = [
        test_climate_search,
        test_healthcare_search,
        test_party_filter,
        test_budget_search,
        test_fetch_speech,
        test_date_range
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
