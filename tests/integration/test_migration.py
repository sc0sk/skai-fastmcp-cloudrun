"""Integration tests for migration from legacy to langchain-postgres schema.

This test suite validates the migration script's correctness, idempotency,
and data integrity guarantees.

Test Coverage:
- Record count matching (source == target)
- Random spot-check validation (10 records)
- Idempotency (re-running migration is safe)
- Data integrity (content and metadata preserved)
- Collection isolation (migrations don't affect other collections)

Prerequisites:
- Cloud SQL instance accessible
- Source table (hansard_speeches) populated with test data
- VECTOR_BACKEND can be any value (tests work with both backends)

Usage:
    # Run all migration tests
    pytest tests/integration/test_migration.py -v

    # Run specific test class
    pytest tests/integration/test_migration.py::TestMigrationExecution -v

    # Skip if no Cloud SQL access
    pytest tests/integration/test_migration.py --skip-integration
"""

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
SPOT_CHECK_COUNT = 10


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
    return f"test_migration_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def sample_data(engine, test_collection_name) -> List[Dict]:
    """Create sample data in source table for testing.

    Returns:
        List of sample record dictionaries with langchain_id and content
    """
    # Create 20 sample records
    sample_records = []
    for i in range(20):
        sample_records.append(
            {
                "content": f"Test speech content {i}",
                "embedding": [0.1] * 768,  # 768-dim embedding
                "langchain_metadata": {
                    "test_collection": test_collection_name,
                    "test_index": i,
                },
                "speaker": f"Speaker {i % 5}",
                "party": f"Party {i % 3}",
                "chamber": "Representatives" if i % 2 == 0 else "Senate",
            }
        )

    # Insert into source table
    with engine.begin() as conn:
        for record in sample_records:
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {SOURCE_TABLE} 
                        (content, embedding, langchain_metadata, speaker, party, chamber)
                    VALUES 
                        (:content, :embedding::vector, :metadata, :speaker, :party, :chamber)
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

    yield sample_records

    # Cleanup: Remove test records from source
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                DELETE FROM {SOURCE_TABLE}
                WHERE langchain_metadata->>'test_collection' = :test_collection
            """
            ),
            {"test_collection": test_collection_name},
        )


@pytest.fixture(scope="function")
def cleanup_target_collection(engine, test_collection_name):
    """Cleanup target collection after test."""
    yield

    # Cleanup: Remove test collection and its embeddings
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
            conn.execute(
                text(
                    f"""
                    DELETE FROM {TARGET_EMBEDDING_TABLE}
                    WHERE collection_id = :collection_id
                """
                ),
                {"collection_id": collection_uuid},
            )

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


class TestMigrationPrerequisites:
    """Test migration prerequisite validation."""

    def test_source_table_exists(self, engine):
        """Test that source table exists."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                """
                ),
                {"table_name": SOURCE_TABLE},
            )
            exists = result.scalar()

        assert exists, f"Source table {SOURCE_TABLE} does not exist"

    def test_target_tables_exist(self, engine):
        """Test that target tables exist."""
        with engine.connect() as conn:
            for table_name in [TARGET_COLLECTION_TABLE, TARGET_EMBEDDING_TABLE]:
                result = conn.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = :table_name
                        )
                    """
                    ),
                    {"table_name": table_name},
                )
                exists = result.scalar()
                assert exists, f"Target table {table_name} does not exist"

    def test_pgvector_extension_enabled(self, engine):
        """Test that pgvector extension is enabled."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_extension
                        WHERE extname = 'vector'
                    )
                """
                )
            )
            exists = result.scalar()

        assert exists, "pgvector extension is not enabled"


class TestMigrationExecution:
    """Test migration execution and validation."""

    def test_record_count_matching(
        self, engine, sample_data, test_collection_name, cleanup_target_collection
    ):
        """Test that migrated record count matches source count.

        Acceptance Criteria:
        - After migration, target collection has same number of records as source
        - No records lost during migration
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        # Execute migration
        executor = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=5,  # Small batch for testing
            dry_run=False,
        )

        result = executor.execute()

        # Validate counts
        assert result["status"] in [
            "success",
            "warning",
        ], f"Migration failed: {result}"

        # Get actual counts
        with engine.connect() as conn:
            # Source count (filtered by test collection)
            source_result = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {SOURCE_TABLE}
                    WHERE langchain_metadata->>'test_collection' = :test_collection
                """
                ),
                {"test_collection": test_collection_name},
            )
            source_count = source_result.scalar()

            # Target count
            target_result = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {TARGET_EMBEDDING_TABLE} e
                    JOIN {TARGET_COLLECTION_TABLE} c ON e.collection_id = c.uuid
                    WHERE c.name = :collection_name
                """
                ),
                {"collection_name": test_collection_name},
            )
            target_count = target_result.scalar()

        assert (
            source_count == target_count
        ), f"Record count mismatch: source={source_count}, target={target_count}"
        assert source_count == len(
            sample_data
        ), f"Expected {len(sample_data)} records, found {source_count}"

    def test_spot_check_data_integrity(
        self, engine, sample_data, test_collection_name, cleanup_target_collection
    ):
        """Test that 10 random records maintain data integrity.

        Acceptance Criteria:
        - Sample 10 random records from source
        - Verify corresponding target records exist
        - Verify content matches exactly
        - Verify metadata matches exactly
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        # Execute migration
        executor = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=10,
            dry_run=False,
        )

        executor.execute()

        # Spot-check 10 records
        with engine.connect() as conn:
            # Get random sample of langchain_ids
            result = conn.execute(
                text(
                    f"""
                    SELECT langchain_id, content, langchain_metadata, speaker, party, chamber
                    FROM {SOURCE_TABLE}
                    WHERE langchain_metadata->>'test_collection' = :test_collection
                    ORDER BY RANDOM()
                    LIMIT :limit
                """
                ),
                {"test_collection": test_collection_name, "limit": SPOT_CHECK_COUNT},
            )
            source_records = result.fetchall()

            mismatches = []
            for source_rec in source_records:
                (
                    langchain_id,
                    source_content,
                    source_metadata,
                    speaker,
                    party,
                    chamber,
                ) = source_rec
                custom_id = str(langchain_id)

                # Find corresponding target record
                result = conn.execute(
                    text(
                        f"""
                        SELECT e.document, e.cmetadata
                        FROM {TARGET_EMBEDDING_TABLE} e
                        JOIN {TARGET_COLLECTION_TABLE} c ON e.collection_id = c.uuid
                        WHERE c.name = :collection_name
                          AND e.custom_id = :custom_id
                    """
                    ),
                    {"collection_name": test_collection_name, "custom_id": custom_id},
                )
                target_rec = result.fetchone()

                if target_rec is None:
                    mismatches.append(
                        {"custom_id": custom_id, "reason": "Target record not found"}
                    )
                    continue

                target_content, target_metadata = target_rec

                # Verify content match
                if source_content != target_content:
                    mismatches.append(
                        {"custom_id": custom_id, "reason": "Content mismatch"}
                    )
                    continue

                # Verify metadata (source metadata should be subset of target)
                if source_metadata:
                    for key, value in source_metadata.items():
                        if target_metadata.get(key) != value:
                            mismatches.append(
                                {
                                    "custom_id": custom_id,
                                    "reason": f"Metadata mismatch on key '{key}'",
                                }
                            )
                            break

                # Verify additional columns
                if speaker and target_metadata.get("speaker") != speaker:
                    mismatches.append(
                        {"custom_id": custom_id, "reason": "Speaker mismatch"}
                    )
                if party and target_metadata.get("party") != party:
                    mismatches.append(
                        {"custom_id": custom_id, "reason": "Party mismatch"}
                    )
                if chamber and target_metadata.get("chamber") != chamber:
                    mismatches.append(
                        {"custom_id": custom_id, "reason": "Chamber mismatch"}
                    )

        assert (
            len(mismatches) == 0
        ), f"Found {len(mismatches)} data integrity issues: {mismatches}"


class TestMigrationIdempotency:
    """Test migration idempotency (safe re-runs)."""

    def test_second_run_is_noop(
        self, engine, sample_data, test_collection_name, cleanup_target_collection
    ):
        """Test that running migration twice is safe and idempotent.

        Acceptance Criteria:
        - First migration succeeds
        - Second migration succeeds (no errors)
        - Record count remains unchanged after second run
        - No duplicate records created
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        executor = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=10,
            dry_run=False,
        )

        # First migration
        result1 = executor.execute()
        assert result1["status"] in ["success", "warning"]

        # Get count after first migration
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {TARGET_EMBEDDING_TABLE} e
                    JOIN {TARGET_COLLECTION_TABLE} c ON e.collection_id = c.uuid
                    WHERE c.name = :collection_name
                """
                ),
                {"collection_name": test_collection_name},
            )
            count_after_first = result.scalar()

        # Second migration (should be no-op)
        result2 = executor.execute()
        assert result2["status"] in ["success", "warning"]

        # Get count after second migration
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {TARGET_EMBEDDING_TABLE} e
                    JOIN {TARGET_COLLECTION_TABLE} c ON e.collection_id = c.uuid
                    WHERE c.name = :collection_name
                """
                ),
                {"collection_name": test_collection_name},
            )
            count_after_second = result.scalar()

        assert (
            count_after_first == count_after_second
        ), f"Record count changed after second run: {count_after_first} → {count_after_second}"
        assert (
            result2["newly_migrated"] == 0
        ), f"Expected 0 newly migrated, got {result2['newly_migrated']}"

    def test_partial_migration_recovery(
        self, engine, sample_data, test_collection_name, cleanup_target_collection
    ):
        """Test that partial migrations can be safely resumed.

        Simulates a migration that processes some records, then when re-run,
        only processes the remaining records.
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        # First migration with small batch (processes first batch only)
        executor1 = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=5,  # Will process 5 records
            dry_run=False,
        )

        # Manually migrate only first batch
        collection_uuid = executor1.ensure_collection_exists()
        first_batch_count = executor1.migrate_batch(
            collection_uuid=collection_uuid, offset=0, batch_size=5
        )

        assert first_batch_count == 5

        # Second migration with full run (should complete remaining)
        executor2 = MigrationExecutor(
            engine=engine,
            collection_name=test_collection_name,
            batch_size=100,  # Large enough to process all remaining
            dry_run=False,
        )

        result = executor2.execute()

        # Verify all records migrated
        assert result["target_count"] == len(
            sample_data
        ), f"Expected {len(sample_data)} records, got {result['target_count']}"


class TestMigrationCollectionIsolation:
    """Test that migrations don't affect other collections."""

    def test_multiple_collections_isolated(
        self, engine, sample_data, cleanup_target_collection
    ):
        """Test that migrating to one collection doesn't affect others.

        Creates two separate collections and verifies they remain isolated.
        """
        from scripts.migrate_to_langchain_postgres import MigrationExecutor

        collection1 = f"test_col1_{uuid.uuid4().hex[:8]}"
        collection2 = f"test_col2_{uuid.uuid4().hex[:8]}"

        try:
            # Migrate to first collection
            executor1 = MigrationExecutor(
                engine=engine,
                collection_name=collection1,
                batch_size=10,
                dry_run=False,
            )
            result1 = executor1.execute()

            # Migrate to second collection (same source data)
            executor2 = MigrationExecutor(
                engine=engine,
                collection_name=collection2,
                batch_size=10,
                dry_run=False,
            )
            result2 = executor2.execute()

            # Both migrations should succeed
            assert result1["status"] in ["success", "warning"]
            assert result2["status"] in ["success", "warning"]

            # Verify both collections have records
            with engine.connect() as conn:
                for collection_name in [collection1, collection2]:
                    result = conn.execute(
                        text(
                            f"""
                            SELECT COUNT(*) FROM {TARGET_EMBEDDING_TABLE} e
                            JOIN {TARGET_COLLECTION_TABLE} c ON e.collection_id = c.uuid
                            WHERE c.name = :collection_name
                        """
                        ),
                        {"collection_name": collection_name},
                    )
                    count = result.scalar()
                    assert count == len(
                        sample_data
                    ), f"Collection {collection_name} has {count} records, expected {len(sample_data)}"

        finally:
            # Cleanup both collections
            with engine.begin() as conn:
                for collection_name in [collection1, collection2]:
                    # Get collection UUID
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

                        # Delete embeddings
                        conn.execute(
                            text(
                                f"""
                                DELETE FROM {TARGET_EMBEDDING_TABLE}
                                WHERE collection_id = :collection_id
                            """
                            ),
                            {"collection_id": collection_uuid},
                        )

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
