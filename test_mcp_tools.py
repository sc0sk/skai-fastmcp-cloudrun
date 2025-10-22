#!/usr/bin/env python3
"""Test MCP search and fetch tools end-to-end for political communications use cases."""

import asyncio
import sys
import os

# Import the server to access tools directly  
sys.path.insert(0, os.path.dirname(__file__))
from src.server import mcp, search_speeches, fetch_speech_by_id


async def test_political_communications():
    """Test search and fetch tools for various political communications tasks."""

    print("\n" + "="*80)
    print("MCP TOOLS END-TO-END TESTING")
    print("Testing search and fetch for political communications, speech writing, and policy analysis")
    print("="*80)

    # Test 1: Cost of Living Policy Analysis
    print("\n📊 TEST 1: Cost of Living Policy Analysis")
    print("-" * 80)
    print("Query: 'cost of living inflation'")

    results = await search_speeches(
        query="cost of living inflation",
        limit=3
    )

    print(f"✅ Found {len(results)} speeches")
    for i, speech in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Speaker: {speech.get('speaker')}")
        print(f"   Date: {speech.get('date')}")
        print(f"   Themes: {speech.get('themes')}")
        print(f"   Preview: {speech.get('content', '')[:150]}...")

    # Test 2: Housing Affordability Speech Research
    print("\n\n🏠 TEST 2: Housing Affordability Speech Research")
    print("-" * 80)
    print("Query: 'housing affordability rents property market'")

    results = await search_speeches(
        query="housing affordability rents property market",
        limit=3
    )

    print(f"✅ Found {len(results)} speeches")
    for i, speech in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Speaker: {speech.get('speaker')}")
        print(f"   Date: {speech.get('date')}")
        print(f"   Debate: {speech.get('debate')}")
        print(f"   Preview: {speech.get('content', '')[:150]}...")

    # Test 3: Fetch specific speech
    if results and results[0].get('speech_id'):
        speech_id = results[0]['speech_id']
        print(f"\n📝 TEST 3: Fetch Speech {speech_id}")
        print("-" * 80)
        
        speech = await fetch_speech_by_id(speech_id=speech_id)
        
        print(f"✅ Retrieved full speech")
        print(f"   Speaker: {speech.get('speaker')}")
        print(f"   Date: {speech.get('date')}")
        print(f"   Content length: {len(speech.get('content', ''))} characters")

    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/hansard-sa-key.json'
    asyncio.run(test_political_communications())
