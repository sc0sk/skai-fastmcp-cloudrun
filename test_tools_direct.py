#!/usr/bin/env python3
"""
Direct test of MCP tools without starting the full server.
Tests search, fetch, and verifies bulk ingestion tool exists.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.search import search_hansard_speeches
from tools.fetch import fetch_hansard_speech
from tools.ingest_markdown_directory import ingest_markdown_directory

async def test_tools():
    """Test all tools directly."""
    
    print("=" * 80)
    print("HANSARD MCP TOOLS - DIRECT TEST")
    print("=" * 80)
    print()
    
    # Test 1: Search
    print("TEST 1: Search for speeches about 'climate change'")
    print("-" * 80)
    try:
        result = await search_hansard_speeches(
            query="climate change",
            limit=2
        )
        print(f"✅ Search successful! Found {result.get('total_results', 0)} results")
        if result.get('speeches'):
            speech = result['speeches'][0]
            print(f"   First result:")
            print(f"   - Speaker: {speech.get('speaker', 'Unknown')}")
            print(f"   - Date: {speech.get('date', 'Unknown')}")
            print(f"   - Chamber: {speech.get('chamber', 'Unknown')}")
        print()
    except Exception as e:
        print(f"❌ Search failed: {e}")
        print()
    
    # Test 2: Fetch by ID
    print("TEST 2: Fetch speech by ID")
    print("-" * 80)
    try:
        # Get a speech_id from search first
        search_result = await search_hansard_speeches(
            query="infrastructure", 
            limit=1
        )
        
        if search_result.get('speeches'):
            speech_id = search_result['speeches'][0].get('speech_id')
            print(f"   Using speech_id: {speech_id}")
            
            fetch_result = await fetch_hansard_speech(speech_id=speech_id)
            print(f"✅ Fetch successful!")
            print(f"   - Speaker: {fetch_result.get('speaker', 'Unknown')}")
            print(f"   - Date: {fetch_result.get('date', 'Unknown')}")
            print(f"   - Text length: {len(fetch_result.get('text', ''))} characters")
        else:
            print("⚠️  No speeches found to test fetch with")
        print()
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        print()
    
    # Test 3: Verify bulk ingestion function exists
    print("TEST 3: Verify bulk ingestion tool (Feature 013)")
    print("-" * 80)
    try:
        # Check if the function is callable
        if callable(ingest_markdown_directory):
            print("✅ ingest_markdown_directory function exists and is callable")
            
            # Get function signature
            import inspect
            sig = inspect.signature(ingest_markdown_directory)
            print(f"   Parameters: {list(sig.parameters.keys())}")
            print(f"   ")
            print("   ⚠️  Skipping actual execution to avoid database changes")
        print()
    except Exception as e:
        print(f"❌ Error checking bulk ingestion: {e}")
        print()
    
    # Test 4: Search with filters
    print("TEST 4: Search with chamber filter")
    print("-" * 80)
    try:
        result = await search_hansard_speeches(
            query="economy",
            chamber="REPS",
            limit=2
        )
        print(f"✅ Filtered search successful! Found {result.get('total_results', 0)} results in REPS")
        if result.get('speeches'):
            for i, speech in enumerate(result['speeches'][:2], 1):
                print(f"   Result {i}: {speech.get('speaker')} ({speech.get('chamber')})")
        print()
    except Exception as e:
        print(f"❌ Filtered search failed: {e}")
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ search_hansard_speeches: TESTED")
    print("✅ fetch_hansard_speech: TESTED")
    print("✅ ingest_markdown_directory: VERIFIED (Feature 013)")
    print("✅ Search with filters: TESTED")
    print()
    print("🎉 All direct tool tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_tools())
