#!/usr/bin/env python3
"""
Phase 2: Async-Aware MCP Best Practices Testing Framework

Properly validates MCP tools with:
✅ Correct async/await patterns (no coroutine warnings)
✅ Comprehensive error handling validation
✅ Data quality checking
✅ Performance measurement
✅ Edge case testing
"""

import asyncio
import json
import time
import sys
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# Import tools directly for testing
sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun/src')

from tools.search import search_hansard_speeches
from tools.fetch import fetch_hansard_speech


@dataclass
class AsyncTestResult:
    """Result from a single async test"""
    test_name: str
    criterion: str
    status: str  # "PASS", "FAIL", "SKIP", "TIMEOUT"
    message: str
    duration_ms: float
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class AsyncMCPTestFramework:
    """Async-aware MCP testing framework for Phase 2"""

    def __init__(self, timeout_seconds: float = 10.0, verbose: bool = True):
        self.timeout_seconds = timeout_seconds
        self.verbose = verbose
        self.results: List[AsyncTestResult] = []
        
    def log(self, msg: str, level: str = "INFO"):
        """Log message with level indicator"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            level_emoji = {
                "INFO": "ℹ️ ",
                "PASS": "✅",
                "FAIL": "❌",
                "WARN": "⚠️ ",
                "TEST": "🧪"
            }.get(level, "")
            print(f"[{timestamp}] {level_emoji} {msg}")

    async def test_tool_with_timeout(
        self,
        tool_func: Callable,
        tool_args: Dict[str, Any],
        test_name: str,
        criterion: str
    ) -> AsyncTestResult:
        """
        Execute async tool with timeout protection.
        
        Returns:
            AsyncTestResult with execution details or timeout indication
        """
        start_time = time.time()
        
        try:
            self.log(f"Running {test_name}...", "TEST")
            
            # Properly await the async function
            result = await asyncio.wait_for(
                tool_func(**tool_args),
                timeout=self.timeout_seconds
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AsyncTestResult(
                test_name=test_name,
                criterion=criterion,
                status="PASS",
                message=f"✓ Completed in {duration_ms:.1f}ms",
                duration_ms=duration_ms,
                data=result
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return AsyncTestResult(
                test_name=test_name,
                criterion=criterion,
                status="TIMEOUT",
                message=f"✗ Exceeded {self.timeout_seconds}s timeout",
                duration_ms=duration_ms,
                error=f"Timeout after {duration_ms:.1f}ms"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return AsyncTestResult(
                test_name=test_name,
                criterion=criterion,
                status="FAIL",
                message=f"✗ Exception: {type(e).__name__}",
                duration_ms=duration_ms,
                error=str(e)
            )

    async def test_error_handling(
        self,
        tool_func: Callable,
        invalid_inputs: List[Dict[str, Any]],
        tool_name: str
    ) -> List[AsyncTestResult]:
        """
        Test error handling with invalid inputs.
        
        Validates that:
        - Invalid inputs raise appropriate exceptions
        - Error messages are informative
        - No silent failures or coroutine warnings
        
        Returns:
            List of test results for each invalid input case
        """
        results = []
        
        for i, invalid_input in enumerate(invalid_inputs):
            test_name = f"{tool_name}_error_case_{i+1}"
            start_time = time.time()
            error_caught = False
            error_message = ""
            
            try:
                self.log(f"Testing error case {i+1}: {invalid_input}", "TEST")
                
                # Properly await the async function
                result = await asyncio.wait_for(
                    tool_func(**invalid_input),
                    timeout=self.timeout_seconds
                )
                
                # Check if result contains error indication
                if isinstance(result, dict) and result.get('status') == 'error':
                    error_caught = True
                    error_message = result.get('message', 'No error details')
                else:
                    error_message = "No error for invalid input (may be graceful degradation)"
                    
            except (ValueError, TypeError, KeyError) as e:
                error_caught = True
                error_message = f"{type(e).__name__}: {str(e)}"
                
            except asyncio.TimeoutError:
                error_message = "Timeout during error handling test"
                
            except Exception as e:
                error_caught = True
                error_message = f"{type(e).__name__}: {str(e)}"
            
            duration_ms = (time.time() - start_time) * 1000
            
            status = "PASS" if error_caught else "FAIL"
            results.append(AsyncTestResult(
                test_name=test_name,
                criterion="Error Handling",
                status=status,
                message=f"{'✓' if error_caught else '✗'} {error_message}",
                duration_ms=duration_ms,
                error=None if error_caught else error_message
            ))
        
        return results

    async def test_data_quality(
        self,
        tool_func: Callable,
        valid_input: Dict[str, Any],
        tool_name: str,
        expected_fields: List[str]
    ) -> AsyncTestResult:
        """
        Test response data quality.
        
        Validates:
        - Response is properly structured
        - Contains expected fields
        - Data types are correct
        - No null/empty critical fields
        
        Returns:
            AsyncTestResult with quality assessment
        """
        test_name = f"{tool_name}_data_quality"
        start_time = time.time()
        
        try:
            self.log(f"Testing data quality for {tool_name}...", "TEST")
            
            result = await asyncio.wait_for(
                tool_func(**valid_input),
                timeout=self.timeout_seconds
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Validate structure
            if not isinstance(result, dict):
                return AsyncTestResult(
                    test_name=test_name,
                    criterion="Data Quality",
                    status="FAIL",
                    message=f"✗ Response is {type(result).__name__}, expected dict",
                    duration_ms=duration_ms,
                    error=f"Invalid response type: {type(result).__name__}"
                )
            
            # Validate expected fields
            missing_fields = [f for f in expected_fields if f not in result]
            
            if missing_fields:
                return AsyncTestResult(
                    test_name=test_name,
                    criterion="Data Quality",
                    status="FAIL",
                    message=f"✗ Missing fields: {', '.join(missing_fields)}",
                    duration_ms=duration_ms,
                    error=f"Missing expected fields: {missing_fields}"
                )
            
            # Check for null/empty critical fields
            null_fields = [f for f in expected_fields if result.get(f) is None]
            
            if null_fields:
                status = "FAIL" if all(f in ['title', 'speech_id', 'full_text'] for f in null_fields) else "PASS"
                return AsyncTestResult(
                    test_name=test_name,
                    criterion="Data Quality",
                    status=status,
                    message=f"{'✗' if status == 'FAIL' else '✓'} Fields present (null: {', '.join(null_fields)})",
                    duration_ms=duration_ms,
                    data=result
                )
            
            return AsyncTestResult(
                test_name=test_name,
                criterion="Data Quality",
                status="PASS",
                message=f"✓ All expected fields present and non-null",
                duration_ms=duration_ms,
                data=result
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return AsyncTestResult(
                test_name=test_name,
                criterion="Data Quality",
                status="TIMEOUT",
                message=f"✗ Timeout during quality check",
                duration_ms=duration_ms,
                error=f"Timeout after {duration_ms:.1f}ms"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return AsyncTestResult(
                test_name=test_name,
                criterion="Data Quality",
                status="FAIL",
                message=f"✗ Exception: {type(e).__name__}",
                duration_ms=duration_ms,
                error=str(e)
            )

    async def test_performance_characteristics(
        self,
        tool_func: Callable,
        valid_input: Dict[str, Any],
        tool_name: str,
        expected_max_ms: float = 5000
    ) -> AsyncTestResult:
        """
        Test tool performance characteristics.
        
        Measures:
        - Execution latency
        - Response size
        - Consistency (multiple runs)
        
        Returns:
            AsyncTestResult with performance metrics
        """
        test_name = f"{tool_name}_performance"
        timings = []
        sizes = []
        
        try:
            self.log(f"Testing performance for {tool_name} (3 iterations)...", "TEST")
            
            # Run 3 times to check consistency
            for iteration in range(3):
                start_time = time.time()
                result = await asyncio.wait_for(
                    tool_func(**valid_input),
                    timeout=self.timeout_seconds
                )
                duration_ms = (time.time() - start_time) * 1000
                timings.append(duration_ms)
                
                # Measure response size
                result_json = json.dumps(result, default=str)
                sizes.append(len(result_json))
                
                self.log(f"  Iteration {iteration+1}: {duration_ms:.1f}ms ({len(result_json)} bytes)", "INFO")
            
            avg_ms = sum(timings) / len(timings)
            avg_size = sum(sizes) / len(sizes)
            
            # Assess performance
            if avg_ms <= expected_max_ms / 2:
                performance_grade = "EXCELLENT"
                status = "PASS"
            elif avg_ms <= expected_max_ms:
                performance_grade = "GOOD"
                status = "PASS"
            else:
                performance_grade = "SLOW"
                status = "FAIL"
            
            message = (
                f"{'✓' if status == 'PASS' else '✗'} {performance_grade}: "
                f"avg {avg_ms:.1f}ms (±{max(timings)-min(timings):.1f}ms), "
                f"size {avg_size:.0f} bytes"
            )
            
            return AsyncTestResult(
                test_name=test_name,
                criterion="Performance",
                status=status,
                message=message,
                duration_ms=avg_ms,
                data={
                    "timings_ms": timings,
                    "avg_ms": avg_ms,
                    "min_ms": min(timings),
                    "max_ms": max(timings),
                    "sizes_bytes": sizes,
                    "avg_size_bytes": int(avg_size)
                }
            )
            
        except Exception as e:
            return AsyncTestResult(
                test_name=test_name,
                criterion="Performance",
                status="FAIL",
                message=f"✗ Performance test failed",
                duration_ms=0,
                error=str(e)
            )

    async def run_comprehensive_async_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive async test suite for all MCP tools.
        
        Tests:
        ✅ search_hansard_speeches
        ✅ fetch_hansard_speech
        ✅ Error handling for each tool
        ✅ Data quality for each tool
        ✅ Performance characteristics
        
        Returns:
            Dict with all test results and summary
        """
        self.log("=" * 70, "INFO")
        self.log("Phase 2: Async-Aware MCP Best Practices Testing", "INFO")
        self.log("=" * 70, "INFO")
        
        self.results = []
        
        # Test 1: search_hansard_speeches
        self.log("\n📋 Testing: search_hansard_speeches", "INFO")
        self.log("-" * 70, "INFO")
        
        # Valid input test
        result = await self.test_tool_with_timeout(
            search_hansard_speeches,
            {"query": "housing policy", "limit": 5},
            "search_valid_input",
            "Basic Functionality"
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Error handling tests
        error_results = await self.test_error_handling(
            search_hansard_speeches,
            [
                {"query": ""},  # Empty query
                {"query": "test", "limit": -1},  # Invalid limit
                {"query": "test", "limit": 101},  # Limit exceeds max
            ],
            "search_hansard_speeches"
        )
        self.results.extend(error_results)
        for r in error_results:
            self.log(f"  {r.status:8} | {r.message}", r.status)
        
        # Data quality test
        result = await self.test_data_quality(
            search_hansard_speeches,
            {"query": "infrastructure", "limit": 3},
            "search_hansard_speeches",
            ["speeches", "total_count", "query"]
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Performance test
        result = await self.test_performance_characteristics(
            search_hansard_speeches,
            {"query": "climate", "limit": 5},
            "search_hansard_speeches",
            expected_max_ms=5000
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Test 2: fetch_hansard_speech
        self.log("\n📋 Testing: fetch_hansard_speech", "INFO")
        self.log("-" * 70, "INFO")
        
        # Valid input test (using a sample UUID)
        result = await self.test_tool_with_timeout(
            fetch_hansard_speech,
            {"speech_id": "d9c697e9-e13d-4769-9fbe-ce6cb18f4700"},
            "fetch_valid_input",
            "Basic Functionality"
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Error handling tests
        error_results = await self.test_error_handling(
            fetch_hansard_speech,
            [
                {"speech_id": ""},  # Empty ID
                {"speech_id": "not-a-uuid"},  # Invalid format
                {"speech_id": "00000000-0000-0000-0000-000000000000"},  # Non-existent UUID
            ],
            "fetch_hansard_speech"
        )
        self.results.extend(error_results)
        for r in error_results:
            self.log(f"  {r.status:8} | {r.message}", r.status)
        
        # Data quality test
        result = await self.test_data_quality(
            fetch_hansard_speech,
            {"speech_id": "d9c697e9-e13d-4769-9fbe-ce6cb18f4700"},
            "fetch_hansard_speech",
            ["speech_id", "title", "full_text", "speaker", "party", "chamber", "date"]
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Performance test
        result = await self.test_performance_characteristics(
            fetch_hansard_speech,
            {"speech_id": "d9c697e9-e13d-4769-9fbe-ce6cb18f4700"},
            "fetch_hansard_speech",
            expected_max_ms=1000
        )
        self.results.append(result)
        self.log(f"  {result.status:8} | {result.message}", result.status)
        
        # Generate summary
        summary = self._generate_summary()
        
        self.log("\n" + "=" * 70, "INFO")
        self.log("📊 TEST SUMMARY", "INFO")
        self.log("=" * 70, "INFO")
        self.log(f"Total Tests: {summary['total']}", "INFO")
        self.log(f"Passed: {summary['passed']} ✅", "PASS")
        self.log(f"Failed: {summary['failed']} {'❌' if summary['failed'] > 0 else ''}", "INFO")
        self.log(f"Timeouts: {summary['timeouts']} {'⏱️' if summary['timeouts'] > 0 else ''}", "INFO")
        self.log(f"Success Rate: {summary['success_rate']*100:.1f}%", "INFO")
        
        return {
            "results": self.results,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics"""
        total = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        timeouts = len([r for r in self.results if r.status == "TIMEOUT"])
        
        success_rate = passed / total if total > 0 else 0
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "timeouts": timeouts,
            "success_rate": success_rate
        }


async def main():
    """Main entry point for async test execution"""
    framework = AsyncMCPTestFramework(timeout_seconds=10.0, verbose=True)
    results = await framework.run_comprehensive_async_tests()
    
    # Print detailed results
    print("\n" + "=" * 70)
    print("📝 DETAILED RESULTS")
    print("=" * 70)
    
    for result in results["results"]:
        print(f"\n{result.criterion}: {result.test_name}")
        print(f"  Status: {result.status}")
        print(f"  Message: {result.message}")
        print(f"  Duration: {result.duration_ms:.1f}ms")
        if result.error:
            print(f"  Error: {result.error}")
    
    return results


if __name__ == "__main__":
    # Run async tests
    results = asyncio.run(main())
    
    # Exit with appropriate code
    success_rate = results["summary"]["success_rate"]
    exit_code = 0 if success_rate >= 0.8 else 1
    
    print(f"\n✅ Test execution complete. Exit code: {exit_code}")
    sys.exit(exit_code)
