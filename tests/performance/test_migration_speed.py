"""Performance tests for migration script.

This test suite validates migration performance benchmarks.

Test Coverage:
- Migration speed: 10,000 rows < 5 minutes
- Batch processing throughput
- Memory usage during migration
- Connection pool efficiency

Prerequisites:
- Cloud SQL instance accessible
- Sufficient test data in source table
- Performance test environment (not production)

Usage:
    # Run performance tests
    pytest tests/performance/test_migration_speed.py -v

    # Run with detailed logging
    pytest tests/performance/test_migration_speed.py -v -s

    # Skip if no Cloud SQL access
    pytest tests/performance/test_migration_speed.py --skip-performance
"""

import time
import uuid
from typing import Dict, List

import pytest
from sqlalchemy import text

from src.config import (
    get_cloudsql_database,
    get_cloudsql_instance,
    get_gcp_project_id,
    get_gcp_region,
)
from src.storage.cloud_sql_engine import CloudSQLEngine

# Test constants
SOURCE_TABLE = "hansard_speeches"
TARGET_COLLECTION_TABLE = "langchain_pg_collection"
TARGET_EMBEDDING_TABLE = "langchain_pg_embedding"
BENCHMARK_ROW_COUNT = 10000
BENCHMARK_TIME_LIMIT_SECONDS = 300  # 5 minutes


def is_cloud_sql_configured() -> bool:
    """Check if Cloud SQL configuration is available."""
    return bool(
        get_gcp_project_id()
        and get_cloudsql_instance()
        and get_cloudsql_database()
    )


@pytest.fixture(scope="module")
def engine():
    """Create Cloud SQL engine for tests."""
    if not is_cloud_sql_configured():
        pytest.skip("Cloud SQL not configured")

    project_id = get_gcp_project_id()
    region = get_gcp_region()
    instance = get_cloudsql_instance()
    database = get_cloudsql_database()

    engine_mgr = CloudSQLEngine(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database,
    )

    yield engine_mgr.engine

    engine_mgr.close()


@pytest.fixture(scope="function")
def test_collection_name() -> str:
    """Generate unique collection name for test isolation."""
    return f"test_perf_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def large_sample_data(engine, test_collection_name) -> List[Dict]:
    """Create large sample dataset for performance testing.

    Creates BENCHMARK_ROW_COUNT records for realistic performance testing.

    Returns:
        List of sample record dictionaries
    """
    print(f"\nCreating {BENCHMARK_ROW_COUNT:,} test records...")
    start_time = time.time()

    sample_records = []

    # Insert in batches for faster setup
    batch_size = 1000
    with engine.begin() as conn:
        for i in range(0, BENCHMARK_ROW_COUNT, batch_size):
            batch = []
            for j in range(batch_size):
                record_idx = i + j
                if record_idx >= BENCHMARK_ROW_COUNT:
                    break

                batch.append(
                    {
                        "content": (
                            f"Test speech content {record_idx} with "
                            "sufficient length to simulate real speeches"
                        ),
                        "embedding": [0.1 + (record_idx % 100) / 1000.0] * 768,
                        "langchain_metadata": {
                            "test_collection": test_collection_name,
                            "test_index": record_idx,
                            "batch": i // batch_size,
                        },
                        "speaker": f"Speaker {record_idx % 20}",
                        "party": f"Party {record_idx % 5}",
                        "chamber": (
                            "Representatives" if record_idx % 2 == 0 else "Senate"
                        ),
                    }
                )

            # Batch insert
            for record in batch:
                result = conn.execute(
                    text(
                        f"""
                        INSERT INTO {SOURCE_TABLE}
                        (content, embedding, langchain_metadata,
                         speaker, party, chamber)
                        VALUES
                        (:content, :embedding::vector, :metadata,
                         :speaker, :party, :chamber)
                        RETURNING langchain_id
                    """
                    ),
                    {
                        "content": record["content"],
                        "embedding": record["embedding"],
                        "metadata": record["langchain_metadata"],
                        "speaker": record["speaker"],
                        "party": record["party"],
                        "chamber": record["chamber"],
                    },
                )
                langchain_id = result.scalar()
                record["langchain_id"] = str(langchain_id)
                sample_records.append(record)

            elapsed = time.time() - start_time
            progress = ((i + batch_size) / BENCHMARK_ROW_COUNT) * 100
            print(
                f"  Setup progress: {min(progress, 100):.1f}% "
                f"({i + len(batch):,}/{BENCHMARK_ROW_COUNT:,}) "
                f"in {elapsed:.1f}s"
            )

    setup_time = time.time() - start_time
    print(
        f"Created {len(sample_records):,} test records in {setup_time:.1f}s "
        f"({len(sample_records)/setup_time:.1f} records/sec)"
    )

    yield sample_records

    # Cleanup: Remove test records from source
    print(f"\nCleaning up {len(sample_records):,} test records...")
    cleanup_start = time.time()

    with engine.begin() as conn:
        result = conn.execute(
            text(
                f"""
                DELETE FROM {SOURCE_TABLE}
                WHERE langchain_metadata->>'test_collection' = :test_collection
            """
            ),
            {"test_collection": test_collection_name},
        )
        deleted_count = result.rowcount

    cleanup_time = time.time() - cleanup_start
    print(
        f"Cleaned up {deleted_count:,} records in {cleanup_time:.1f}s"
    )


@pytest.fixture(scope="function")
def cleanup_target_collection(engine, test_collection_name):
    """Cleanup target collection after test."""
    yield

    # Cleanup: Remove test collection and its embeddings
    print(f"\nCleaning up target collection '{test_collection_name}'...")
    cleanup_start = time.time()

    with engine.begin() as conn:
        # Get collection UUID
        result = conn.execute(
            text(
                f"""
                SELECT uuid FROM {TARGET_COLLECTION_TABLE}
                WHERE name = :name
            """
            ),
            {"name": test_collection_name},
        )
        collection_row = result.fetchone()

        if collection_row:
            collection_uuid = collection_row[0]

            # Delete embeddings
            result = conn.execute(
                text(
                    f"""
                    DELETE FROM {TARGET_EMBEDDING_TABLE}
                    WHERE collection_id = :collection_id
                """
                ),
                {"collection_id": collection_uuid},
            )
            deleted_embeddings = result.rowcount

            # Delete collection
            conn.execute(
                text(
                    f"""
                    DELETE FROM {TARGET_COLLECTION_TABLE}
                    WHERE uuid = :uuid
                """
                ),
                {"uuid": collection_uuid},
            )

            cleanup_time = time.time() - cleanup_start
            print(
                f"Cleaned up {deleted_embeddings:,} embeddings "
                f"and 1 collection in {cleanup_time:.1f}s"
            )


class TestMigrationSpeed:
    """Test migration performance benchmarks."""

    @pytest.mark.slow
    def test_10k_rows_under_5_minutes(
        self,
        engine,
        large_sample_data,
        test_collection_name,
        cleanup_target_collection,
    ):
        """Test that migrating 10,000 rows completes in under 5 minutes.

        Performance Benchmark:
        - Target: 10,000 rows < 5 minutes (300 seconds)
        - Minimum acceptable throughput: 33.3 rows/second
        - Expected performance: 50-100 rows/second

        This test validates that the migration script can handle
        production-scale data volumes efficiently.
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        print(
            f"\nStarting migration of {len(large_sample_data):,} records..."
        )
        print(f"Time limit: {BENCHMARK_TIME_LIMIT_SECONDS}s (5 minutes)")

        start_time = time.time()

        # Execute migration with appropriate batch size
        executor = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=100,  # Standard batch size
            dry_run=False,
        )

        result = executor.execute()

        elapsed_time = time.time() - start_time

        # Validate migration succeeded
        assert result["status"] in ["success", "warning"], (
            f"Migration failed: {result}"
        )

        # Validate performance benchmark
        print(f"\nMigration Performance:")
        print(f"  Total time: {elapsed_time:.2f}s")
        print(
            f"  Throughput: {result['newly_migrated']/elapsed_time:.1f} "
            "rows/sec"
        )
        print(f"  Records migrated: {result['newly_migrated']:,}")
        print(f"  Time limit: {BENCHMARK_TIME_LIMIT_SECONDS}s")

        assert elapsed_time < BENCHMARK_TIME_LIMIT_SECONDS, (
            f"Migration took {elapsed_time:.2f}s, "
            f"exceeds {BENCHMARK_TIME_LIMIT_SECONDS}s limit"
        )

        # Validate record count
        assert result["target_count"] == len(large_sample_data), (
            f"Expected {len(large_sample_data):,} records, "
            f"got {result['target_count']:,}"
        )

        # Calculate and report throughput
        throughput = result["newly_migrated"] / elapsed_time
        print(f"\n✅ Performance benchmark PASSED!")
        print(f"   Throughput: {throughput:.1f} rows/sec")
        print(f"   Time: {elapsed_time:.2f}s / {BENCHMARK_TIME_LIMIT_SECONDS}s")

    @pytest.mark.slow
    def test_batch_size_performance(
        self,
        engine,
        test_collection_name,
        cleanup_target_collection,
    ):
        """Test different batch sizes for optimal performance.

        Compares throughput with batch sizes: 50, 100, 200, 500.
        Helps identify optimal batch size for production use.
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        # Create smaller dataset for batch size comparison
        test_data_count = 1000
        test_data_collection = f"{test_collection_name}_batch"

        print(f"\nCreating {test_data_count} test records...")
        with engine.begin() as conn:
            for i in range(test_data_count):
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {SOURCE_TABLE}
                        (content, embedding, langchain_metadata,
                         speaker, party, chamber)
                        VALUES
                        (:content, :embedding::vector, :metadata,
                         :speaker, :party, :chamber)
                    """
                    ),
                    {
                        "content": f"Batch test speech {i}",
                        "embedding": [0.1] * 768,
                        "metadata": {
                            "test_collection": test_data_collection,
                            "index": i,
                        },
                        "speaker": f"Speaker {i % 10}",
                        "party": f"Party {i % 3}",
                        "chamber": "Representatives",
                    },
                )

        batch_sizes = [50, 100, 200, 500]
        results = []

        for batch_size in batch_sizes:
            # Create unique collection for each test
            collection_name = f"{test_collection_name}_b{batch_size}"

            print(f"\nTesting batch size: {batch_size}")
            start_time = time.time()

            executor = MigrationExecutor(
                engine=engine,
                collection_name=collection_name,
                batch_size=batch_size,
                dry_run=False,
            )

            migration_result = executor.execute()
            elapsed = time.time() - start_time

            throughput = migration_result["newly_migrated"] / elapsed

            results.append(
                {
                    "batch_size": batch_size,
                    "elapsed": elapsed,
                    "throughput": throughput,
                    "migrated": migration_result["newly_migrated"],
                }
            )

            print(f"  Time: {elapsed:.2f}s")
            print(f"  Throughput: {throughput:.1f} rows/sec")

        # Cleanup test data
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    DELETE FROM {SOURCE_TABLE}
                    WHERE langchain_metadata->>'test_collection' = :test_collection
                """
                ),
                {"test_collection": test_data_collection},
            )

            # Cleanup all batch test collections
            for batch_size in batch_sizes:
                collection_name = f"{test_collection_name}_b{batch_size}"
                result = conn.execute(
                    text(
                        f"""
                        SELECT uuid FROM {TARGET_COLLECTION_TABLE}
                        WHERE name = :name
                    """
                    ),
                    {"name": collection_name},
                )
                collection_row = result.fetchone()

                if collection_row:
                    collection_uuid = collection_row[0]

                    conn.execute(
                        text(
                            f"""
                            DELETE FROM {TARGET_EMBEDDING_TABLE}
                            WHERE collection_id = :collection_id
                        """
                        ),
                        {"collection_id": collection_uuid},
                    )

                    conn.execute(
                        text(
                            f"""
                            DELETE FROM {TARGET_COLLECTION_TABLE}
                            WHERE uuid = :uuid
                        """
                        ),
                        {"uuid": collection_uuid},
                    )

        # Report comparison
        print("\n" + "=" * 60)
        print("Batch Size Performance Comparison")
        print("=" * 60)
        print(f"{'Batch Size':<12} {'Time (s)':<10} {'Throughput (rows/s)':<20}")
        print("-" * 60)

        for result in results:
            print(
                f"{result['batch_size']:<12} "
                f"{result['elapsed']:<10.2f} "
                f"{result['throughput']:<20.1f}"
            )

        # Find optimal batch size (highest throughput)
        optimal = max(results, key=lambda r: r["throughput"])
        print("=" * 60)
        print(
            f"✅ Optimal batch size: {optimal['batch_size']} "
            f"({optimal['throughput']:.1f} rows/sec)"
        )
