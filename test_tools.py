#!/usr/bin/env python3
"""Test MCP tools (search and fetch) and score responses."""

import asyncio
import json
from src.tools.search import search_speeches
from src.tools.fetch import fetch_speech, get_dataset_stats


async def test_search_tool():
    """Test search tool with various queries."""
    print("\n" + "="*80)
    print("TESTING SEARCH TOOL")
    print("="*80)

    test_queries = [
        {
            "query": "climate change renewable energy",
            "limit": 5,
            "description": "Semantic search for climate/energy topics"
        },
        {
            "query": "housing affordability cost of living",
            "limit": 3,
            "description": "Semantic search for housing/cost topics"
        },
        {
            "query": "infrastructure projects",
            "limit": 3,
            "speaker": "Simon Kennedy",
            "description": "Infrastructure speeches by Simon Kennedy"
        }
    ]

    results = []

    for test in test_queries:
        print(f"\n\n📊 Test Query: {test['description']}")
        print(f"   Query: '{test['query']}'")
        print(f"   Limit: {test['limit']}")
        if 'speaker' in test:
            print(f"   Speaker: {test['speaker']}")
        print("-" * 80)

        try:
            search_results = await search_speeches(
                query=test['query'],
                limit=test['limit'],
                speaker=test.get('speaker'),
            )

            print(f"\n✅ Found {len(search_results)} results\n")

            for i, result in enumerate(search_results, 1):
                print(f"Result {i}:")
                print(f"  Speech ID: {result['speech_id']}")
                print(f"  Speaker: {result['speaker']} ({result['party']})")
                print(f"  Date: {result['date']}")
                print(f"  Relevance Score: {result['relevance_score']:.3f}")
                print(f"  Excerpt: {result['excerpt'][:200]}...")
                print()

            # Score this query
            score = {
                "query": test['query'],
                "description": test['description'],
                "results_count": len(search_results),
                "relevance_scores": [r['relevance_score'] for r in search_results],
                "avg_relevance": sum(r['relevance_score'] for r in search_results) / len(search_results) if search_results else 0,
                "pass": len(search_results) > 0 and all(r['relevance_score'] > 0.5 for r in search_results)
            }
            results.append(score)

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "query": test['query'],
                "description": test['description'],
                "error": str(e),
                "pass": False
            })

    return results


async def test_fetch_tool(speech_id: str):
    """Test fetch tool to retrieve complete speech."""
    print("\n" + "="*80)
    print("TESTING FETCH TOOL")
    print("="*80)

    print(f"\n📄 Fetching speech: {speech_id}")
    print("-" * 80)

    try:
        speech = await fetch_speech(speech_id)

        print(f"\n✅ Successfully fetched speech\n")
        print(f"Speech ID: {speech['speech_id']}")
        print(f"Title: {speech['title']}")
        print(f"Speaker: {speech['speaker']} ({speech['party']})")
        print(f"Chamber: {speech['chamber']}")
        print(f"Date: {speech['date']}")
        print(f"Word Count: {speech['word_count']}")
        print(f"\nFull Text Preview: {speech['full_text'][:500]}...")

        # Score fetch
        score = {
            "speech_id": speech_id,
            "fetched": True,
            "has_full_text": len(speech['full_text']) > 0,
            "word_count": speech['word_count'],
            "pass": True
        }
        return score

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "speech_id": speech_id,
            "error": str(e),
            "pass": False
        }


async def test_dataset_stats():
    """Test dataset statistics resource."""
    print("\n" + "="*80)
    print("TESTING DATASET STATS")
    print("="*80)

    try:
        stats = await get_dataset_stats()

        print(f"\n✅ Dataset Statistics:\n")
        print(json.dumps(stats, indent=2))

        return {
            "speech_count": stats.get('speech_count', 0),
            "unique_speakers": stats.get('unique_speakers', 0),
            "pass": stats.get('speech_count', 0) > 0
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e), "pass": False}


async def main():
    """Run all tests and generate score report."""

    # Test dataset stats first
    stats_score = await test_dataset_stats()

    # Test search tool
    search_scores = await test_search_tool()

    # Get a speech ID from search results for fetch test
    speech_id = None
    if search_scores and search_scores[0].get('results_count', 0) > 0:
        # Re-run first search to get speech_id
        first_result = await search_speeches(
            query="climate change renewable energy",
            limit=1
        )
        if first_result:
            speech_id = first_result[0]['speech_id']

    # Test fetch tool
    fetch_score = None
    if speech_id:
        fetch_score = await test_fetch_tool(speech_id)

    # Generate final score report
    print("\n" + "="*80)
    print("FINAL SCORE REPORT")
    print("="*80)

    print("\n📊 Search Tool Scores:")
    for score in search_scores:
        status = "✅ PASS" if score.get('pass') else "❌ FAIL"
        print(f"\n{status} - {score['description']}")
        if 'avg_relevance' in score:
            print(f"  Avg Relevance: {score['avg_relevance']:.3f}")
            print(f"  Results Count: {score['results_count']}")

    if fetch_score:
        status = "✅ PASS" if fetch_score.get('pass') else "❌ FAIL"
        print(f"\n\n📄 Fetch Tool Score:")
        print(f"{status} - Retrieved speech with {fetch_score.get('word_count', 0)} words")

    status = "✅ PASS" if stats_score.get('pass') else "❌ FAIL"
    print(f"\n\n📈 Dataset Stats Score:")
    print(f"{status} - {stats_score.get('speech_count', 0)} speeches, {stats_score.get('unique_speakers', 0)} speakers")

    # Overall pass rate
    all_scores = search_scores + ([fetch_score] if fetch_score else []) + [stats_score]
    pass_count = sum(1 for s in all_scores if s.get('pass'))
    total_count = len(all_scores)
    pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0

    print(f"\n\n🎯 OVERALL SCORE: {pass_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
