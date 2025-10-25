"""Performance tests for search latency comparison.

This test suite validates search performance benchmarks between legacy and postgres backends.

Test Coverage:
- Search latency percentiles (P50, P95, P99)
- Backend comparison (postgres within 10% of legacy)
- Query complexity scenarios (simple, filtered, multi-filter)
- Throughput under load

Prerequisites:
- Cloud SQL instance accessible
- Both backends have equivalent test data
- Performance test environment (not production)

Usage:
    # Run performance tests
    pytest tests/performance/test_search_latency.py -v

    # Run with detailed logging
    pytest tests/performance/test_search_latency.py -v -s

    # Skip if no Cloud SQL access
    pytest tests/performance/test_search_latency.py --skip-performance

Acceptance Criteria:
- P95 latency for postgres backend ≤ 110% of legacy backend
- P50 latency for postgres backend ≤ 110% of legacy backend
- P99 latency for postgres backend ≤ 120% of legacy backend (more tolerance)
"""

import asyncio
import os
import statistics
import time
import uuid
from typing import Dict, List, Tuple

import pytest

from src.config import get_vector_backend
from src.storage.vector_store import get_default_vector_store


def is_cloud_sql_configured() -> bool:
    """Check if Cloud SQL configuration is available."""
    # Basic check - can we import and initialize vector stores
    try:
        from src.config import (
            get_cloudsql_database,
            get_cloudsql_instance,
            get_gcp_project_id,
        )

        return bool(
            get_gcp_project_id()
            and get_cloudsql_instance()
            and get_cloudsql_database()
        )
    except Exception:
        return False


# Mark all tests in this module as slow
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def test_queries() -> List[str]:
    """Provide test queries for performance testing.
    
    Returns diverse queries to test various scenarios:
    - Simple topic queries
    - Complex multi-word queries
    - Policy-specific queries
    """
    return [
        "climate change policy",
        "healthcare reform legislation",
        "education funding allocation",
        "indigenous rights recognition",
        "housing affordability crisis",
        "infrastructure investment projects",
        "taxation policy reform",
        "renewable energy transition",
        "national security strategy",
        "trade agreement negotiations",
        "employment and wages",
        "social welfare programs",
        "agricultural subsidies",
        "digital privacy protection",
        "immigration policy reform",
    ]


@pytest.fixture(scope="module")
def test_filters() -> List[Dict[str, str]]:
    """Provide test metadata filters.
    
    Returns various filter combinations to test filtering performance.
    """
    return [
        {},  # No filter
        {"chamber": "Representatives"},
        {"chamber": "Senate"},
        {"party": "Labor"},
        {"party": "Liberal"},
        {"chamber": "Representatives", "party": "Labor"},
        {"chamber": "Senate", "party": "Liberal"},
    ]


class LatencyStats:
    """Container for latency statistics."""

    def __init__(self, measurements: List[float]):
        """Initialize stats from measurements.
        
        Args:
            measurements: List of latency measurements in seconds
        """
        if not measurements:
            raise ValueError("Cannot compute stats from empty measurements")

        sorted_measurements = sorted(measurements)
        self.measurements = sorted_measurements
        self.count = len(sorted_measurements)
        self.min = sorted_measurements[0]
        self.max = sorted_measurements[-1]
        self.mean = statistics.mean(sorted_measurements)
        self.median = statistics.median(sorted_measurements)
        self.p50 = self._percentile(sorted_measurements, 50)
        self.p95 = self._percentile(sorted_measurements, 95)
        self.p99 = self._percentile(sorted_measurements, 99)

    @staticmethod
    def _percentile(sorted_data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data.
        
        Args:
            sorted_data: Pre-sorted list of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Value at specified percentile
        """
        if not sorted_data:
            return 0.0

        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1

        if c >= len(sorted_data):
            return sorted_data[-1]

        d0 = sorted_data[f]
        d1 = sorted_data[c]
        return d0 + (d1 - d0) * (k - f)

    def __repr__(self) -> str:
        """String representation of stats."""
        return (
            f"LatencyStats(count={self.count}, "
            f"mean={self.mean:.3f}s, "
            f"p50={self.p50:.3f}s, "
            f"p95={self.p95:.3f}s, "
            f"p99={self.p99:.3f}s)"
        )


async def measure_search_latency(
    vector_store,
    query: str,
    k: int = 10,
    filter_dict: Dict[str, str] = None,
) -> float:
    """Measure latency for a single search operation.
    
    Args:
        vector_store: Vector store service instance
        query: Query text
        k: Number of results to return
        filter_dict: Optional metadata filters
        
    Returns:
        Latency in seconds
    """
    start_time = time.perf_counter()

    await vector_store.similarity_search(
        query=query,
        k=k,
        filter=filter_dict,
    )

    end_time = time.perf_counter()
    return end_time - start_time


async def run_latency_benchmark(
    backend: str,
    queries: List[str],
    filters: List[Dict[str, str]],
    iterations: int = 10,
) -> Tuple[LatencyStats, Dict[str, LatencyStats]]:
    """Run comprehensive latency benchmark for a backend.
    
    Args:
        backend: Backend name ('legacy' or 'postgres')
        queries: List of test queries
        filters: List of filter dictionaries
        iterations: Number of iterations per query/filter combination
        
    Returns:
        Tuple of (overall_stats, breakdown_by_scenario)
    """
    # Temporarily override backend
    original_backend = os.environ.get("VECTOR_BACKEND")
    os.environ["VECTOR_BACKEND"] = backend

    try:
        # Create vector store for this backend
        vector_store = get_default_vector_store()

        all_measurements = []
        breakdown = {}

        # Warm-up: Run a few searches to initialize connections
        warmup_query = queries[0]
        for _ in range(3):
            await measure_search_latency(vector_store, warmup_query)

        # Run benchmarks
        for query in queries:
            for filter_dict in filters:
                scenario_name = f"query_len_{len(query.split())}_filters_{len(filter_dict)}"
                scenario_measurements = []

                for _ in range(iterations):
                    latency = await measure_search_latency(
                        vector_store,
                        query,
                        filter_dict=filter_dict if filter_dict else None,
                    )
                    all_measurements.append(latency)
                    scenario_measurements.append(latency)

                breakdown[scenario_name] = LatencyStats(scenario_measurements)

        overall_stats = LatencyStats(all_measurements)
        return overall_stats, breakdown

    finally:
        # Restore original backend
        if original_backend is not None:
            os.environ["VECTOR_BACKEND"] = original_backend
        else:
            os.environ.pop("VECTOR_BACKEND", None)


@pytest.mark.asyncio
async def test_search_latency_comparison(test_queries, test_filters):
    """Test search latency comparison between backends.
    
    Validates:
    - P95 latency for postgres ≤ 110% of legacy
    - P50 latency for postgres ≤ 110% of legacy
    - P99 latency for postgres ≤ 120% of legacy
    
    This is the primary acceptance criteria test.
    """
    if not is_cloud_sql_configured():
        pytest.skip("Cloud SQL not configured")

    print("\n" + "=" * 80)
    print("Search Latency Benchmark: Legacy vs Postgres")
    print("=" * 80)

    # Run benchmarks for both backends
    print("\nRunning legacy backend benchmark...")
    legacy_stats, legacy_breakdown = await run_latency_benchmark(
        backend="legacy",
        queries=test_queries[:5],  # Use subset for faster testing
        filters=test_filters[:3],  # Use subset for faster testing
        iterations=10,
    )

    print("\nRunning postgres backend benchmark...")
    postgres_stats, postgres_breakdown = await run_latency_benchmark(
        backend="postgres",
        queries=test_queries[:5],  # Same subset
        filters=test_filters[:3],  # Same subset
        iterations=10,
    )

    # Print results
    print("\n" + "-" * 80)
    print("OVERALL RESULTS")
    print("-" * 80)
    print(f"Legacy:   {legacy_stats}")
    print(f"Postgres: {postgres_stats}")

    # Calculate percentage differences
    p50_diff = (postgres_stats.p50 / legacy_stats.p50 - 1.0) * 100
    p95_diff = (postgres_stats.p95 / legacy_stats.p95 - 1.0) * 100
    p99_diff = (postgres_stats.p99 / legacy_stats.p99 - 1.0) * 100

    print("\n" + "-" * 80)
    print("PERCENTAGE DIFFERENCES (postgres vs legacy)")
    print("-" * 80)
    print(f"P50: {p50_diff:+.1f}% (threshold: +10%)")
    print(f"P95: {p95_diff:+.1f}% (threshold: +10%)")
    print(f"P99: {p99_diff:+.1f}% (threshold: +20%)")

    # Print per-scenario breakdown
    print("\n" + "-" * 80)
    print("SCENARIO BREAKDOWN")
    print("-" * 80)
    for scenario_name in sorted(legacy_breakdown.keys()):
        legacy_scenario = legacy_breakdown[scenario_name]
        postgres_scenario = postgres_breakdown[scenario_name]
        scenario_p95_diff = (
            postgres_scenario.p95 / legacy_scenario.p95 - 1.0
        ) * 100
        print(
            f"{scenario_name:30s} "
            f"Legacy P95: {legacy_scenario.p95:.3f}s  "
            f"Postgres P95: {postgres_scenario.p95:.3f}s  "
            f"Diff: {scenario_p95_diff:+.1f}%"
        )

    print("\n" + "=" * 80)

    # Assertions (acceptance criteria)
    assert (
        postgres_stats.p50 <= legacy_stats.p50 * 1.10
    ), f"P50 latency regression: postgres {postgres_stats.p50:.3f}s > legacy {legacy_stats.p50:.3f}s * 1.10"

    assert (
        postgres_stats.p95 <= legacy_stats.p95 * 1.10
    ), f"P95 latency regression: postgres {postgres_stats.p95:.3f}s > legacy {legacy_stats.p95:.3f}s * 1.10"

    assert (
        postgres_stats.p99 <= legacy_stats.p99 * 1.20
    ), f"P99 latency regression: postgres {postgres_stats.p99:.3f}s > legacy {legacy_stats.p99:.3f}s * 1.20"

    print("\n✅ All latency acceptance criteria passed!")


@pytest.mark.asyncio
async def test_search_latency_absolute_thresholds(test_queries):
    """Test absolute latency thresholds for postgres backend.
    
    Validates:
    - P95 latency < 2 seconds (reasonable user experience)
    - P50 latency < 1 second (good user experience)
    - P99 latency < 5 seconds (acceptable for edge cases)
    
    These are absolute thresholds independent of legacy performance.
    """
    if not is_cloud_sql_configured():
        pytest.skip("Cloud SQL not configured")

    print("\n" + "=" * 80)
    print("Search Latency Benchmark: Absolute Thresholds (Postgres)")
    print("=" * 80)

    # Run benchmark for postgres backend only
    postgres_stats, postgres_breakdown = await run_latency_benchmark(
        backend="postgres",
        queries=test_queries[:5],  # Use subset
        filters=[{}, {"chamber": "Representatives"}],  # Simple filters
        iterations=10,
    )

    # Print results
    print("\n" + "-" * 80)
    print("RESULTS")
    print("-" * 80)
    print(f"Postgres: {postgres_stats}")

    # Print thresholds
    print("\n" + "-" * 80)
    print("THRESHOLD CHECKS")
    print("-" * 80)
    print(
        f"P50: {postgres_stats.p50:.3f}s "
        f"({'✅ PASS' if postgres_stats.p50 < 1.0 else '❌ FAIL'}, threshold: <1.0s)"
    )
    print(
        f"P95: {postgres_stats.p95:.3f}s "
        f"({'✅ PASS' if postgres_stats.p95 < 2.0 else '❌ FAIL'}, threshold: <2.0s)"
    )
    print(
        f"P99: {postgres_stats.p99:.3f}s "
        f"({'✅ PASS' if postgres_stats.p99 < 5.0 else '❌ FAIL'}, threshold: <5.0s)"
    )

    print("\n" + "=" * 80)

    # Assertions (absolute thresholds)
    assert (
        postgres_stats.p50 < 1.0
    ), f"P50 latency too high: {postgres_stats.p50:.3f}s (threshold: <1.0s)"

    assert (
        postgres_stats.p95 < 2.0
    ), f"P95 latency too high: {postgres_stats.p95:.3f}s (threshold: <2.0s)"

    assert (
        postgres_stats.p99 < 5.0
    ), f"P99 latency too high: {postgres_stats.p99:.3f}s (threshold: <5.0s)"

    print("\n✅ All absolute latency thresholds passed!")


@pytest.mark.asyncio
async def test_search_throughput_under_load(test_queries):
    """Test search throughput under concurrent load.
    
    Validates:
    - System handles 20 concurrent searches
    - Average latency remains acceptable under load
    - No connection pool exhaustion
    """
    if not is_cloud_sql_configured():
        pytest.skip("Cloud SQL not configured")

    print("\n" + "=" * 80)
    print("Search Throughput Under Load (Postgres)")
    print("=" * 80)

    # Override to use postgres backend
    original_backend = os.environ.get("VECTOR_BACKEND")
    os.environ["VECTOR_BACKEND"] = "postgres"

    try:
        vector_store = get_default_vector_store()

        # Warm-up
        await measure_search_latency(vector_store, test_queries[0])

        # Run concurrent searches
        concurrent_requests = 20
        queries_per_request = 5

        async def run_concurrent_searches():
            """Run multiple searches concurrently."""
            latencies = []
            for query in test_queries[:queries_per_request]:
                latency = await measure_search_latency(vector_store, query)
                latencies.append(latency)
            return latencies

        print(f"\nRunning {concurrent_requests} concurrent search batches...")
        print(f"Each batch performs {queries_per_request} searches")

        start_time = time.perf_counter()

        # Create concurrent tasks
        tasks = [
            run_concurrent_searches() for _ in range(concurrent_requests)
        ]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Flatten results
        all_latencies = [latency for batch in results for latency in batch]
        stats = LatencyStats(all_latencies)

        # Calculate throughput
        total_searches = concurrent_requests * queries_per_request
        throughput = total_searches / total_time

        print("\n" + "-" * 80)
        print("RESULTS")
        print("-" * 80)
        print(f"Total searches: {total_searches}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} searches/sec")
        print(f"Latency stats: {stats}")

        print("\n" + "=" * 80)

        # Assertions
        assert (
            stats.p95 < 3.0
        ), f"P95 latency under load too high: {stats.p95:.3f}s (threshold: <3.0s)"

        assert (
            throughput > 10.0
        ), f"Throughput too low: {throughput:.2f} searches/sec (threshold: >10/sec)"

        print("\n✅ Throughput test passed!")

    finally:
        # Restore original backend
        if original_backend is not None:
            os.environ["VECTOR_BACKEND"] = original_backend
        else:
            os.environ.pop("VECTOR_BACKEND", None)


@pytest.mark.asyncio
async def test_cold_start_latency(test_queries):
    """Test cold start latency for first search after initialization.
    
    Validates:
    - Cold start completes in reasonable time
    - Subsequent searches benefit from warm cache
    """
    if not is_cloud_sql_configured():
        pytest.skip("Cloud SQL not configured")

    print("\n" + "=" * 80)
    print("Cold Start Latency Test (Postgres)")
    print("=" * 80)

    # Override to use postgres backend
    original_backend = os.environ.get("VECTOR_BACKEND")
    os.environ["VECTOR_BACKEND"] = "postgres"

    try:
        # Create fresh vector store (cold start)
        vector_store = get_default_vector_store()
        query = test_queries[0]

        # Measure cold start
        print("\nMeasuring cold start latency...")
        cold_start_latency = await measure_search_latency(vector_store, query)

        # Measure warm subsequent searches
        print("Measuring warm search latency...")
        warm_latencies = []
        for _ in range(10):
            latency = await measure_search_latency(vector_store, query)
            warm_latencies.append(latency)

        warm_stats = LatencyStats(warm_latencies)

        print("\n" + "-" * 80)
        print("RESULTS")
        print("-" * 80)
        print(f"Cold start latency: {cold_start_latency:.3f}s")
        print(f"Warm search P50: {warm_stats.p50:.3f}s")
        print(f"Warm search P95: {warm_stats.p95:.3f}s")
        print(
            f"Cold start overhead: {cold_start_latency - warm_stats.p50:.3f}s"
        )

        print("\n" + "=" * 80)

        # Assertions
        assert (
            cold_start_latency < 5.0
        ), f"Cold start too slow: {cold_start_latency:.3f}s (threshold: <5.0s)"

        assert (
            warm_stats.p95 < 2.0
        ), f"Warm P95 too high: {warm_stats.p95:.3f}s (threshold: <2.0s)"

        print("\n✅ Cold start test passed!")

    finally:
        # Restore original backend
        if original_backend is not None:
            os.environ["VECTOR_BACKEND"] = original_backend
        else:
            os.environ.pop("VECTOR_BACKEND", None)
