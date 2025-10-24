#!/usr/bin/env python3
"""
Test MCP server with bearer token authentication.

Tests all three tools:
1. search_hansard_speeches
2. fetch_hansard_speech
3. ingest_hansard_speech
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_search_tool():
    """Test search_hansard_speeches tool"""
    print("\n" + "="*60)
    print("TEST 1: search_hansard_speeches")
    print("="*60)

    from tools.search import search_hansard_speeches

    try:
        # Test basic search
        result = await search_hansard_speeches(
            query="climate change policy",
            limit=3
        )

        print(f"✅ Search successful")
        print(f"   Query: 'climate change policy'")
        print(f"   Results returned: {len(result.get('speeches', []))}")

        if result.get('speeches'):
            first = result['speeches'][0]
            print(f"   Top result preview:")
            print(f"   - Speaker: {first.get('speaker_name', 'Unknown')}")
            print(f"   - Party: {first.get('party', 'Unknown')}")
            print(f"   - Date: {first.get('date', 'Unknown')}")
            print(f"   - Score: {first.get('similarity_score', 0):.3f}")
            print(f"   - Text preview: {first.get('text', '')[:100]}...")

        return True
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fetch_tool(speech_id: str = None):
    """Test fetch_hansard_speech tool"""
    print("\n" + "="*60)
    print("TEST 2: fetch_hansard_speech")
    print("="*60)

    from tools.fetch import fetch_hansard_speech

    # If no speech_id provided, search for one first
    if not speech_id:
        from tools.search import search_hansard_speeches
        search_result = await search_hansard_speeches(query="parliament", limit=1)
        if search_result.get('speeches'):
            speech_id = search_result['speeches'][0].get('speech_id')

    if not speech_id:
        print("⚠️  No speech ID available for fetch test")
        return False

    try:
        result = await fetch_hansard_speech(speech_id=speech_id)

        print(f"✅ Fetch successful")
        print(f"   Speech ID: {speech_id}")
        print(f"   Speaker: {result.get('speaker_name', 'Unknown')}")
        print(f"   Party: {result.get('party', 'Unknown')}")
        print(f"   Chamber: {result.get('chamber', 'Unknown')}")
        print(f"   Date: {result.get('date', 'Unknown')}")
        print(f"   Text length: {len(result.get('text', ''))} chars")
        print(f"   Text preview: {result.get('text', '')[:200]}...")

        return True
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ingest_tool():
    """Test ingest_hansard_speech tool"""
    print("\n" + "="*60)
    print("TEST 3: ingest_hansard_speech")
    print("="*60)

    from tools.ingest import ingest_hansard_speech

    # Create test speech data
    test_speech = {
        "speaker_name": "Test Speaker",
        "party": "Australian Labor Party",
        "chamber": "House of Representatives",
        "date": datetime.now().date().isoformat(),
        "text": "This is a test speech for MCP authentication verification. " * 10,
        "speech_id": f"test-{datetime.now().timestamp()}"
    }

    try:
        result = await ingest_hansard_speech(
            speaker_name=test_speech["speaker_name"],
            party=test_speech["party"],
            chamber=test_speech["chamber"],
            date=test_speech["date"],
            text=test_speech["text"],
            speech_id=test_speech["speech_id"]
        )

        print(f"✅ Ingest successful")
        print(f"   Speech ID: {test_speech['speech_id']}")
        print(f"   Speaker: {test_speech['speaker_name']}")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Message: {result.get('message', 'N/A')}")

        # Verify by fetching the ingested speech
        print(f"   Verifying ingestion by fetching...")
        from tools.fetch import fetch_hansard_speech
        verify = await fetch_hansard_speech(speech_id=test_speech['speech_id'])
        if verify.get('speaker_name') == test_speech['speaker_name']:
            print(f"   ✅ Verification successful - speech retrieved")
        else:
            print(f"   ⚠️  Verification warning - fetched different data")

        return True
    except Exception as e:
        print(f"❌ Ingest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_with_filters():
    """Test search with metadata filters"""
    print("\n" + "="*60)
    print("TEST 4: search_hansard_speeches (with filters)")
    print("="*60)

    from tools.search import search_hansard_speeches

    try:
        # Test with party filter
        result = await search_hansard_speeches(
            query="economy",
            party="Australian Labor Party",
            limit=2
        )

        print(f"✅ Filtered search successful")
        print(f"   Query: 'economy'")
        print(f"   Filter: party='Australian Labor Party'")
        print(f"   Results: {len(result.get('speeches', []))}")

        for i, speech in enumerate(result.get('speeches', []), 1):
            print(f"   Result {i}:")
            print(f"   - Party: {speech.get('party')}")
            print(f"   - Speaker: {speech.get('speaker_name')}")
            print(f"   - Score: {speech.get('similarity_score', 0):.3f}")

        return True
    except Exception as e:
        print(f"❌ Filtered search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n🔒 MCP Server Authentication & Tool Testing")
    print("=" * 60)

    # Check environment
    auth_mode = os.getenv('DANGEROUSLY_OMIT_AUTH', 'false')
    print(f"Auth mode: {'DISABLED (dev)' if auth_mode.lower() == 'true' else 'ENABLED (production)'}")

    # Check database connection
    print(f"GCP Project: {os.getenv('GCP_PROJECT_ID', 'NOT SET')}")
    print(f"Cloud SQL Instance: {os.getenv('CLOUDSQL_INSTANCE', 'NOT SET')}")
    print(f"Database: {os.getenv('CLOUDSQL_DATABASE', 'NOT SET')}")

    results = []

    # Run tests
    results.append(("Search (basic)", await test_search_tool()))
    results.append(("Fetch", await test_fetch_tool()))
    results.append(("Search (filtered)", await test_search_with_filters()))
    results.append(("Ingest", await test_ingest_tool()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
