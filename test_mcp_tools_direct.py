#!/usr/bin/env python3
"""Test MCP server tools programmatically."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_tools():
    """Test search and fetch tools."""
    print("="*70)
    print("Testing MCP Server Tools")
    print("="*70)
    
    # Import tools
    from src.tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
    from src.tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA
    
    # Test 1: Search tool
    print("\n" + "="*70)
    print("Test 1: Search Tool")
    print("="*70)
    print(f"\nTool Name: {SEARCH_TOOL_METADATA['name']}")
    
    # Get description from function docstring
    doc = search_hansard_speeches.__doc__
    print(f"Description: {doc[:200]}...")
    
    # Get annotations
    annotations = SEARCH_TOOL_METADATA.get('annotations')
    if annotations:
        print(f"\nAnnotations:")
        print(f"  Title: {annotations.title}")
        print(f"  Read-only: {annotations.readOnlyHint}")
        print(f"  Destructive: {annotations.destructiveHint}")
        print(f"  Idempotent: {annotations.idempotentHint}")
    
    print("\n--- Testing search with query 'climate change' ---")
    search_result = None  # Initialize before try block
    try:
        search_result = await search_hansard_speeches(
            query="climate change",
            limit=3
        )
        print(f"\n✅ Search successful!")
        print(f"Total results: {search_result.get('total_count', 0)}")
        print(f"Results returned: {len(search_result.get('speeches', []))}")
        
        if search_result.get('speeches'):
            print("\nFirst result preview:")
            first = search_result['speeches'][0]
            print(f"  Speech ID: {first.get('speech_id')}")
            print(f"  Speaker: {first.get('speaker')}")
            print(f"  Date: {first.get('date')}")
            print(f"  Relevance: {first.get('relevance_score', 0):.3f}")
            print(f"  Preview: {first.get('excerpt', '')[:100]}...")
    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Fetch tool (if we have a speech_id from search)
    if search_result and search_result.get('speeches'):
        print("\n" + "="*70)
        print("Test 2: Fetch Tool")
        print("="*70)
        print(f"\nTool Name: {FETCH_TOOL_METADATA['name']}")
        
        # Get description from function docstring
        doc = fetch_hansard_speech.__doc__
        print(f"Description: {doc[:200]}...")
        
        # Get annotations
        annotations = FETCH_TOOL_METADATA.get('annotations')
        if annotations:
            print(f"\nAnnotations:")
            print(f"  Title: {annotations.title}")
            print(f"  Read-only: {annotations.readOnlyHint}")
            print(f"  Destructive: {annotations.destructiveHint}")
            print(f"  Idempotent: {annotations.idempotentHint}")
        
        speech_id = search_result['speeches'][0]['speech_id']
        print(f"\n--- Fetching speech {speech_id} ---")
        
        try:
            fetch_result = await fetch_hansard_speech(speech_id=speech_id)
            print(f"\n✅ Fetch successful!")
            print(f"Title: {fetch_result.get('title')}")
            print(f"Speaker: {fetch_result.get('speaker')}")
            print(f"Party: {fetch_result.get('party')}")
            print(f"Chamber: {fetch_result.get('chamber')}")
            print(f"Date: {fetch_result.get('date')}")
            print(f"Word count: {fetch_result.get('word_count')}")
            print(f"Full text length: {len(fetch_result.get('full_text', ''))}")
            print(f"Topic tags: {fetch_result.get('topic_tags', [])}")
        except Exception as e:
            print(f"\n❌ Fetch failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Tool Metadata Evaluation")
    print("="*70)
    
    # Evaluate search tool
    print("\nSearch Tool Evaluation:")
    annotations = SEARCH_TOOL_METADATA.get('annotations')
    if annotations:
        print(f"  - readOnlyHint: {annotations.readOnlyHint}")
        print(f"  - Title: {annotations.title}")
    print(f"  - Has 'Use this when' guidance: {'Use this when' in (search_hansard_speeches.__doc__ or '')}")
    print(f"  - Has 'Do not use' guidance: {'Do not use' in (search_hansard_speeches.__doc__ or '')}")
    
    # Evaluate fetch tool
    print("\nFetch Tool Evaluation:")
    annotations = FETCH_TOOL_METADATA.get('annotations')
    if annotations:
        print(f"  - readOnlyHint: {annotations.readOnlyHint}")
        print(f"  - Title: {annotations.title}")
    print(f"  - Has 'Use this when' guidance: {'Use this when' in (fetch_hansard_speech.__doc__ or '')}")
    print(f"  - Has 'Do not use' guidance: {'Do not use' in (fetch_hansard_speech.__doc__ or '')}")
    
    print("\n" + "="*70)
    print("Tests Complete!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_tools())
