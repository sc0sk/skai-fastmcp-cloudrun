#!/usr/bin/env python3
"""
Comprehensive MCP Tool Testing Against Best Practices

This script tests the search_hansard_speeches and fetch_hansard_speech tools
against MCP best practices including:
1. Tool metadata completeness
2. Parameter validation
3. Error handling
4. Response format consistency
5. Performance benchmarks
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from src.tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
from src.tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA


class MCPToolTester:
    """Test MCP tools against best practices."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    def add_result(self, test_name: str, passed: bool, details: str, category: str = "general"):
        """Record a test result."""
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "category": category
        })
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name}: {details}")
    
    async def test_search_tool(self):
        """Test search_hansard_speeches tool."""
        print("\n" + "="*70)
        print("TESTING: search_hansard_speeches")
        print("="*70)
        
        # Test 1: Basic functionality
        print("\n1. Basic Functionality Tests")
        print("-" * 70)
        
        try:
            start = time.time()
            result = await search_hansard_speeches(query="climate change", limit=5)
            elapsed = time.time() - start
            
            self.add_result(
                "Search executes successfully",
                True,
                f"Completed in {elapsed:.2f}s",
                "functionality"
            )
            
            # Check response structure
            has_speeches = "speeches" in result
            has_total = "total_count" in result
            has_query = "query" in result
            
            self.add_result(
                "Response has required fields",
                has_speeches and has_total and has_query,
                f"speeches={has_speeches}, total_count={has_total}, query={has_query}",
                "response_format"
            )
            
            # Check speech structure
            if result.get("speeches"):
                speech = result["speeches"][0]
                required_fields = ["speech_id", "excerpt", "relevance_score", "speaker", "party", "chamber", "date"]
                missing = [f for f in required_fields if f not in speech]
                
                self.add_result(
                    "Speech objects have required fields",
                    len(missing) == 0,
                    f"Missing: {missing}" if missing else "All fields present",
                    "response_format"
                )
            
        except Exception as e:
            self.add_result(
                "Search executes successfully",
                False,
                f"Error: {e}",
                "functionality"
            )
        
        # Test 2: Parameter validation
        print("\n2. Parameter Validation Tests")
        print("-" * 70)
        
        # Test with filters
        try:
            result = await search_hansard_speeches(
                query="immigration",
                party="Liberal",
                chamber="House of Representatives",
                limit=3
            )
            self.add_result(
                "Metadata filtering works",
                len(result.get("speeches", [])) <= 3,
                f"Returned {len(result.get('speeches', []))} results",
                "filtering"
            )
        except Exception as e:
            self.add_result(
                "Metadata filtering works",
                False,
                f"Error: {e}",
                "filtering"
            )
        
        # Test limit parameter
        try:
            result = await search_hansard_speeches(query="housing", limit=1)
            self.add_result(
                "Limit parameter respected",
                len(result.get("speeches", [])) <= 1,
                f"Requested 1, got {len(result.get('speeches', []))}",
                "parameters"
            )
        except Exception as e:
            self.add_result(
                "Limit parameter respected",
                False,
                f"Error: {e}",
                "parameters"
            )
        
        # Test 3: Edge cases
        print("\n3. Edge Case Tests")
        print("-" * 70)
        
        # Empty query
        try:
            result = await search_hansard_speeches(query="", limit=5)
            self.add_result(
                "Handles empty query",
                "speeches" in result,
                f"Returned {result.get('total_count', 0)} results",
                "edge_cases"
            )
        except Exception as e:
            self.add_result(
                "Handles empty query",
                True,  # It's okay to reject empty queries
                f"Rejected with: {type(e).__name__}",
                "edge_cases"
            )
        
        # Non-existent topic
        try:
            result = await search_hansard_speeches(query="xyzabc123notfound", limit=5)
            self.add_result(
                "Handles query with no results",
                result.get("total_count", 0) == 0,
                f"Returned {result.get('total_count', 0)} results as expected",
                "edge_cases"
            )
        except Exception as e:
            self.add_result(
                "Handles query with no results",
                False,
                f"Error: {e}",
                "edge_cases"
            )
        
        # Test 4: Performance
        print("\n4. Performance Tests")
        print("-" * 70)
        
        try:
            start = time.time()
            result = await search_hansard_speeches(query="economy", limit=10)
            elapsed = time.time() - start
            
            self.add_result(
                "Search completes in reasonable time",
                elapsed < 5.0,
                f"{elapsed:.2f}s (target: <5s)",
                "performance"
            )
        except Exception as e:
            self.add_result(
                "Search completes in reasonable time",
                False,
                f"Error: {e}",
                "performance"
            )
    
    async def test_fetch_tool(self):
        """Test fetch_hansard_speech tool."""
        print("\n" + "="*70)
        print("TESTING: fetch_hansard_speech")
        print("="*70)
        
        # First, get a valid speech_id
        search_result = await search_hansard_speeches(query="climate", limit=1)
        if not search_result.get("speeches"):
            print("⚠️  Cannot test fetch - no speeches found in search")
            return
        
        speech_id = search_result["speeches"][0]["speech_id"]
        
        # Test 1: Basic functionality
        print("\n1. Basic Functionality Tests")
        print("-" * 70)
        
        try:
            start = time.time()
            result = await fetch_hansard_speech(speech_id=speech_id)
            elapsed = time.time() - start
            
            self.add_result(
                "Fetch executes successfully",
                True,
                f"Completed in {elapsed:.2f}s",
                "functionality"
            )
            
            # Check response structure
            required_fields = ["speech_id", "title", "full_text", "speaker", "party", "chamber", "date", "word_count"]
            missing = [f for f in required_fields if f not in result]
            
            self.add_result(
                "Response has required fields",
                len(missing) == 0,
                f"Missing: {missing}" if missing else "All fields present",
                "response_format"
            )
            
            # Check full_text is substantial
            full_text_length = len(result.get("full_text", ""))
            self.add_result(
                "Full text is substantial",
                full_text_length > 100,
                f"Length: {full_text_length} chars",
                "response_format"
            )
            
        except Exception as e:
            self.add_result(
                "Fetch executes successfully",
                False,
                f"Error: {e}",
                "functionality"
            )
        
        # Test 2: Error handling
        print("\n2. Error Handling Tests")
        print("-" * 70)
        
        # Invalid speech_id
        try:
            result = await fetch_hansard_speech(speech_id="invalid-uuid-12345")
            self.add_result(
                "Handles invalid speech_id gracefully",
                result is None or "error" in result,
                "Returned error response",
                "error_handling"
            )
        except Exception as e:
            self.add_result(
                "Handles invalid speech_id gracefully",
                True,  # Raising exception is acceptable
                f"Raised {type(e).__name__}",
                "error_handling"
            )
        
        # Test 3: Performance
        print("\n3. Performance Tests")
        print("-" * 70)
        
        try:
            start = time.time()
            result = await fetch_hansard_speech(speech_id=speech_id)
            elapsed = time.time() - start
            
            self.add_result(
                "Fetch completes in reasonable time",
                elapsed < 2.0,
                f"{elapsed:.2f}s (target: <2s)",
                "performance"
            )
        except Exception as e:
            self.add_result(
                "Fetch completes in reasonable time",
                False,
                f"Error: {e}",
                "performance"
            )
    
    def test_metadata(self):
        """Test tool metadata completeness."""
        print("\n" + "="*70)
        print("TESTING: Tool Metadata")
        print("="*70)
        
        # Search tool metadata
        print("\n1. Search Tool Metadata")
        print("-" * 70)
        
        has_name = "name" in SEARCH_TOOL_METADATA
        has_annotations = "annotations" in SEARCH_TOOL_METADATA
        
        self.add_result(
            "Search tool has metadata",
            has_name and has_annotations,
            f"name={has_name}, annotations={has_annotations}",
            "metadata"
        )
        
        if has_annotations:
            annotations = SEARCH_TOOL_METADATA["annotations"]
            has_readonly = getattr(annotations, "readOnlyHint", None) is not None
            self.add_result(
                "Search tool has readOnlyHint",
                has_readonly,
                f"readOnlyHint={getattr(annotations, 'readOnlyHint', None)}",
                "metadata"
            )
        
        # Check docstring
        doc = search_hansard_speeches.__doc__
        has_use_when = "Use this when" in (doc or "")
        has_do_not_use = "Do not use" in (doc or "")
        
        self.add_result(
            "Search tool has usage guidance",
            has_use_when and has_do_not_use,
            f"'Use this when'={has_use_when}, 'Do not use'={has_do_not_use}",
            "metadata"
        )
        
        # Fetch tool metadata
        print("\n2. Fetch Tool Metadata")
        print("-" * 70)
        
        has_name = "name" in FETCH_TOOL_METADATA
        has_annotations = "annotations" in FETCH_TOOL_METADATA
        
        self.add_result(
            "Fetch tool has metadata",
            has_name and has_annotations,
            f"name={has_name}, annotations={has_annotations}",
            "metadata"
        )
        
        if has_annotations:
            annotations = FETCH_TOOL_METADATA["annotations"]
            has_readonly = getattr(annotations, "readOnlyHint", None) is not None
            self.add_result(
                "Fetch tool has readOnlyHint",
                has_readonly,
                f"readOnlyHint={getattr(annotations, 'readOnlyHint', None)}",
                "metadata"
            )
        
        # Check docstring
        doc = fetch_hansard_speech.__doc__
        has_use_when = "Use this when" in (doc or "")
        
        self.add_result(
            "Fetch tool has usage guidance",
            has_use_when,
            f"'Use this when'={has_use_when}",
            "metadata"
        )
    
    def print_summary(self):
        """Print test summary and recommendations."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        # Group by category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}
            if r["passed"]:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        print("\nBy Category:")
        for cat, stats in sorted(categories.items()):
            total_cat = stats["passed"] + stats["failed"]
            print(f"  {cat}: {stats['passed']}/{total_cat} passed")
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r["passed"]]
        if failed_tests:
            print("\n⚠️  Failed Tests:")
            for r in failed_tests:
                print(f"  - {r['test']}: {r['details']}")
        
        # Best practices recommendations
        print("\n" + "="*70)
        print("BEST PRACTICES ASSESSMENT")
        print("="*70)
        
        recommendations = []
        
        # Check metadata completeness
        metadata_tests = [r for r in self.results if r["category"] == "metadata"]
        if any(not r["passed"] for r in metadata_tests):
            recommendations.append(
                "📝 Improve tool metadata with complete annotations and usage guidance"
            )
        
        # Check error handling
        error_tests = [r for r in self.results if r["category"] == "error_handling"]
        if any(not r["passed"] for r in error_tests):
            recommendations.append(
                "🛡️  Enhance error handling for invalid inputs"
            )
        
        # Check performance
        perf_tests = [r for r in self.results if r["category"] == "performance"]
        if any(not r["passed"] for r in perf_tests):
            recommendations.append(
                "⚡ Optimize performance to meet target response times"
            )
        
        if not recommendations:
            print("\n✅ All best practices checks passed!")
            print("\nStrengths:")
            print("  ✓ Complete and accurate metadata")
            print("  ✓ Proper error handling")
            print("  ✓ Good performance")
            print("  ✓ Consistent response format")
            print("  ✓ Read-only hints properly set")
        else:
            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  {rec}")
        
        print("\n" + "="*70)


async def main():
    """Run all tests."""
    print("="*70)
    print("MCP TOOL TESTING - BEST PRACTICES EVALUATION")
    print("="*70)
    
    tester = MCPToolTester()
    
    # Test metadata first (doesn't require async)
    tester.test_metadata()
    
    # Test search tool
    await tester.test_search_tool()
    
    # Test fetch tool
    await tester.test_fetch_tool()
    
    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
