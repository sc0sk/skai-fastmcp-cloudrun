#!/usr/bin/env python3
"""Migration script from legacy schema to langchain-postgres schema.

This script migrates data from the existing hansard_speeches table
(used by langchain-google-cloud-sql-pg) to the new langchain-postgres
schema (langchain_pg_collection and langchain_pg_embedding tables).

Usage:
    # Dry run (preview migration without changes)
    python scripts/migrate_to_langchain_postgres.py --dry-run

    # Execute migration
    python scripts/migrate_to_langchain_postgres.py --execute

    # Execute with custom batch size
    python scripts/migrate_to_langchain_postgres.py --execute --batch-size 200

    # Execute with specific collection name
    python scripts/migrate_to_langchain_postgres.py --execute --collection hansard_v2

Features:
    - Dry-run mode for safe validation before execution
    - Batch processing (default 100 rows) to manage memory
    - Progress reporting with estimated time remaining
    - Transaction rollback on failure
    - Record count validation
    - Random spot-check validation (10 records)
    - Idempotent (re-running safely skips existing records)
    - Preserves custom_id = chunk_id mapping

Migration Strategy:
    1. Validate source table exists and has data
    2. Create/verify langchain_pg_collection exists
    3. Batch read from hansard_speeches
    4. Transform to langchain-postgres format
    5. Insert into langchain_pg_embedding (using custom_id as unique key)
    6. Validate record counts match
    7. Spot-check 10 random records for data integrity
    8. Run ANALYZE for query optimization

Schema Mapping:
    Source (hansard_speeches) → Target (langchain_pg_embedding)
    - langchain_id → ignored (new UUIDs generated)
    - content → document (TEXT)
    - embedding → embedding (VECTOR)
    - langchain_metadata + other columns → cmetadata (JSONB)
    - langchain_id (as string) → custom_id (VARCHAR, unique key)
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import (
    get_cloudsql_database,
    get_cloudsql_instance,
    get_gcp_project_id,
    get_gcp_region,
    get_pgvector_collection,
)
from src.storage.cloud_sql_engine import CloudSQLEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
SOURCE_TABLE = "hansard_speeches"
TARGET_COLLECTION_TABLE = "langchain_pg_collection"
TARGET_EMBEDDING_TABLE = "langchain_pg_embedding"
DEFAULT_BATCH_SIZE = 100
SPOT_CHECK_COUNT = 10


class MigrationError(Exception):
    """Base exception for migration errors."""

    pass


class MigrationValidator:
    """Validates migration prerequisites and results."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def validate_source_table(self) -> Tuple[bool, int]:
        """Validate source table exists and has data.

        Returns:
            Tuple of (exists: bool, row_count: int)
        """
        with self.engine.connect() as conn:
            # Check table exists
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

            if not exists:
                return False, 0

            # Count rows
            result = conn.execute(text(f"SELECT COUNT(*) FROM {SOURCE_TABLE}"))
            row_count = result.scalar()

            return True, row_count

    def validate_target_schema(self) -> bool:
        """Validate langchain-postgres tables exist.

        Returns:
            True if both collection and embedding tables exist
        """
        with self.engine.connect() as conn:
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
                if not exists:
                    logger.error(f"Target table {table_name} does not exist")
                    return False

        return True

    def get_record_counts(
        self, collection_name: str
    ) -> Tuple[int, int]:
        """Get record counts from source and target.

        Args:
            collection_name: Collection name to filter target records

        Returns:
            Tuple of (source_count, target_count)
        """
        with self.engine.connect() as conn:
            # Source count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {SOURCE_TABLE}"))
            source_count = result.scalar()

            # Target count (for this collection)
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
            target_count = result.scalar()

            return source_count, target_count

    def spot_check_records(
        self, collection_name: str, count: int = SPOT_CHECK_COUNT
    ) -> List[Dict[str, Any]]:
        """Randomly sample records and compare source vs target.

        Args:
            collection_name: Collection name to filter target records
            count: Number of records to sample

        Returns:
            List of comparison results with 'match' status
        """
        with self.engine.connect() as conn:
            # Get random sample of langchain_ids from source
            result = conn.execute(
                text(
                    f"""
                    SELECT langchain_id, content, langchain_metadata
                    FROM {SOURCE_TABLE}
                    ORDER BY RANDOM()
                    LIMIT :count
                """
                ),
                {"count": count},
            )
            source_records = result.fetchall()

            comparisons = []
            for source_rec in source_records:
                langchain_id = str(source_rec[0])
                source_content = source_rec[1]
                source_metadata = source_rec[2] or {}

                # Find corresponding target record by custom_id
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
                    {"collection_name": collection_name, "custom_id": langchain_id},
                )
                target_rec = result.fetchone()

                if target_rec is None:
                    comparisons.append(
                        {
                            "custom_id": langchain_id,
                            "match": False,
                            "reason": "Target record not found",
                        }
                    )
                    continue

                target_content = target_rec[0]
                target_metadata = target_rec[1] or {}

                # Compare content and metadata
                content_match = source_content == target_content
                metadata_match = source_metadata == target_metadata

                comparisons.append(
                    {
                        "custom_id": langchain_id,
                        "match": content_match and metadata_match,
                        "content_match": content_match,
                        "metadata_match": metadata_match,
                    }
                )

            return comparisons


class MigrationExecutor:
    """Executes the migration from legacy to langchain-postgres schema."""

    def __init__(
        self,
        engine: Engine,
        collection_name: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
    ):
        self.engine = engine
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.validator = MigrationValidator(engine)

    def ensure_collection_exists(self) -> str:
        """Ensure the target collection exists in langchain_pg_collection.

        Returns:
            Collection UUID as string
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would ensure collection '{self.collection_name}' exists")
            return "dry-run-uuid"

        with self.engine.begin() as conn:
            # Check if collection exists
            result = conn.execute(
                text(
                    f"""
                    SELECT uuid FROM {TARGET_COLLECTION_TABLE}
                    WHERE name = :name
                """
                ),
                {"name": self.collection_name},
            )
            existing = result.fetchone()

            if existing:
                collection_uuid = str(existing[0])
                logger.info(
                    f"Collection '{self.collection_name}' already exists "
                    f"(uuid: {collection_uuid})"
                )
                return collection_uuid

            # Create new collection
            result = conn.execute(
                text(
                    f"""
                    INSERT INTO {TARGET_COLLECTION_TABLE} (name, cmetadata)
                    VALUES (:name, :cmetadata)
                    RETURNING uuid
                """
                ),
                {"name": self.collection_name, "cmetadata": {}},
            )
            collection_uuid = str(result.fetchone()[0])
            logger.info(
                f"Created collection '{self.collection_name}' "
                f"(uuid: {collection_uuid})"
            )
            return collection_uuid

    def migrate_batch(
        self, collection_uuid: str, offset: int, batch_size: int
    ) -> int:
        """Migrate a batch of records from source to target.

        Args:
            collection_uuid: Target collection UUID
            offset: Starting offset in source table
            batch_size: Number of records to process

        Returns:
            Number of records migrated in this batch
        """
        if self.dry_run:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        f"""
                        SELECT COUNT(*) FROM {SOURCE_TABLE}
                        OFFSET :offset LIMIT :limit
                    """
                    ),
                    {"offset": offset, "limit": batch_size},
                )
                count = result.scalar()
                logger.info(
                    f"[DRY RUN] Would migrate batch at offset {offset}: {count} records"
                )
                return count

        with self.engine.begin() as conn:
            # Read batch from source
            result = conn.execute(
                text(
                    f"""
                    SELECT 
                        langchain_id,
                        content,
                        embedding,
                        langchain_metadata,
                        speaker,
                        party,
                        chamber,
                        date,
                        speech_type,
                        electorate,
                        speaker_id,
                        utterance_id,
                        debate
                    FROM {SOURCE_TABLE}
                    ORDER BY langchain_id
                    OFFSET :offset LIMIT :limit
                """
                ),
                {"offset": offset, "limit": batch_size},
            )
            batch = result.fetchall()

            if not batch:
                return 0

            # Transform and insert each record
            migrated_count = 0
            for row in batch:
                (
                    langchain_id,
                    content,
                    embedding,
                    langchain_metadata,
                    speaker,
                    party,
                    chamber,
                    date_val,
                    speech_type,
                    electorate,
                    speaker_id,
                    utterance_id,
                    debate,
                ) = row

                # Build cmetadata from langchain_metadata + additional columns
                cmetadata = dict(langchain_metadata) if langchain_metadata else {}

                # Add non-null additional fields to metadata
                if speaker:
                    cmetadata["speaker"] = speaker
                if party:
                    cmetadata["party"] = party
                if chamber:
                    cmetadata["chamber"] = chamber
                if date_val:
                    cmetadata["date"] = str(date_val)
                if speech_type:
                    cmetadata["speech_type"] = speech_type
                if electorate:
                    cmetadata["electorate"] = electorate
                if speaker_id:
                    cmetadata["speaker_id"] = speaker_id
                if utterance_id:
                    cmetadata["utterance_id"] = utterance_id
                if debate:
                    cmetadata["debate"] = debate

                # Use langchain_id as custom_id for idempotency
                custom_id = str(langchain_id)

                # Insert into target (ON CONFLICT DO NOTHING for idempotency)
                try:
                    conn.execute(
                        text(
                            f"""
                            INSERT INTO {TARGET_EMBEDDING_TABLE} 
                                (collection_id, embedding, document, cmetadata, custom_id)
                            VALUES 
                                (:collection_id, :embedding, :document, :cmetadata, :custom_id)
                            ON CONFLICT (collection_id, custom_id) DO NOTHING
                        """
                        ),
                        {
                            "collection_id": collection_uuid,
                            "embedding": embedding,
                            "document": content,
                            "cmetadata": cmetadata,
                            "custom_id": custom_id,
                        },
                    )
                    migrated_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to migrate record {custom_id}: {e}",
                        exc_info=True,
                    )
                    raise MigrationError(
                        f"Failed to migrate record {custom_id}"
                    ) from e

            return migrated_count

    def execute(self) -> Dict[str, Any]:
        """Execute the full migration.

        Returns:
            Dictionary with migration statistics
        """
        start_time = time.time()

        # Validate prerequisites
        logger.info("Validating migration prerequisites...")

        exists, source_count = self.validator.validate_source_table()
        if not exists:
            raise MigrationError(f"Source table {SOURCE_TABLE} does not exist")

        if source_count == 0:
            logger.warning(f"Source table {SOURCE_TABLE} is empty, nothing to migrate")
            return {
                "status": "success",
                "source_count": 0,
                "target_count": 0,
                "migrated": 0,
                "duration_seconds": 0,
            }

        logger.info(f"Source table has {source_count:,} records")

        if not self.dry_run and not self.validator.validate_target_schema():
            raise MigrationError("Target schema validation failed")

        # Ensure collection exists
        collection_uuid = self.ensure_collection_exists()

        # Get initial target count
        _, initial_target_count = self.validator.get_record_counts(self.collection_name)

        if not self.dry_run:
            logger.info(
                f"Target collection '{self.collection_name}' currently has "
                f"{initial_target_count:,} records"
            )

        # Migrate in batches
        logger.info(
            f"{'[DRY RUN] ' if self.dry_run else ''}"
            f"Starting migration (batch size: {self.batch_size})..."
        )

        total_migrated = 0
        offset = 0
        batch_num = 0

        while offset < source_count:
            batch_num += 1
            batch_start = time.time()

            migrated = self.migrate_batch(collection_uuid, offset, self.batch_size)
            total_migrated += migrated
            offset += self.batch_size

            batch_duration = time.time() - batch_start
            progress_pct = min(100, (offset / source_count) * 100)

            # Estimate remaining time
            if total_migrated > 0:
                elapsed = time.time() - start_time
                rate = total_migrated / elapsed
                remaining = source_count - total_migrated
                eta_seconds = remaining / rate if rate > 0 else 0
                eta = timedelta(seconds=int(eta_seconds))
            else:
                eta = "unknown"

            logger.info(
                f"{'[DRY RUN] ' if self.dry_run else ''}"
                f"Batch {batch_num} complete: {migrated} records "
                f"({batch_duration:.2f}s) | "
                f"Progress: {total_migrated:,}/{source_count:,} "
                f"({progress_pct:.1f}%) | "
                f"ETA: {eta}"
            )

            if migrated == 0:
                break

        # Final validation
        duration = time.time() - start_time

        if not self.dry_run:
            logger.info("Running final validation...")

            # Validate record counts
            source_final, target_final = self.validator.get_record_counts(
                self.collection_name
            )

            newly_migrated = target_final - initial_target_count

            logger.info(f"Migration validation:")
            logger.info(f"  Source records: {source_final:,}")
            logger.info(f"  Target records (before): {initial_target_count:,}")
            logger.info(f"  Target records (after): {target_final:,}")
            logger.info(f"  Newly migrated: {newly_migrated:,}")

            if target_final != source_final:
                logger.warning(
                    f"Record count mismatch! Source: {source_final:,}, "
                    f"Target: {target_final:,}"
                )

            # Spot-check random records
            logger.info(f"Spot-checking {SPOT_CHECK_COUNT} random records...")
            comparisons = self.validator.spot_check_records(
                self.collection_name, SPOT_CHECK_COUNT
            )

            matches = sum(1 for c in comparisons if c["match"])
            logger.info(
                f"Spot-check results: {matches}/{len(comparisons)} records match"
            )

            for comp in comparisons:
                if not comp["match"]:
                    logger.warning(
                        f"Record mismatch: {comp['custom_id']} - {comp.get('reason', 'Data mismatch')}"
                    )

            # Run ANALYZE for query optimization
            logger.info("Running ANALYZE for query optimization...")
            with self.engine.connect() as conn:
                conn.execute(text(f"ANALYZE {TARGET_EMBEDDING_TABLE}"))
                conn.execute(text(f"ANALYZE {TARGET_COLLECTION_TABLE}"))
                conn.commit()

            return {
                "status": "success" if target_final == source_final else "warning",
                "source_count": source_final,
                "target_count": target_final,
                "newly_migrated": newly_migrated,
                "duration_seconds": duration,
                "spot_check_matches": matches,
                "spot_check_total": len(comparisons),
            }
        else:
            logger.info(
                f"[DRY RUN] Would migrate {total_migrated:,} records in {duration:.2f}s"
            )
            return {
                "status": "dry_run",
                "source_count": source_count,
                "would_migrate": total_migrated,
                "duration_seconds": duration,
            }


async def main() -> int:
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate from legacy hansard_speeches to langchain-postgres schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration (safe, no changes)
  %(prog)s --dry-run

  # Execute migration
  %(prog)s --execute

  # Execute with custom batch size
  %(prog)s --execute --batch-size 200

  # Execute with custom collection name
  %(prog)s --execute --collection hansard_v2
        """,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="Execute the migration",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of records to process per batch (default: {DEFAULT_BATCH_SIZE})",
    )

    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Collection name (default: from PGVECTOR_COLLECTION env var)",
    )

    args = parser.parse_args()

    # Get configuration
    project_id = get_gcp_project_id()
    region = get_gcp_region()
    instance = get_cloudsql_instance()
    database = get_cloudsql_database()
    collection_name = args.collection or get_pgvector_collection()

    if not project_id or not instance:
        logger.error(
            "Missing required configuration. Set GCP_PROJECT_ID and CLOUDSQL_INSTANCE"
        )
        return 1

    logger.info("Migration Configuration:")
    logger.info(f"  Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    logger.info(f"  Project: {project_id}")
    logger.info(f"  Region: {region}")
    logger.info(f"  Instance: {instance}")
    logger.info(f"  Database: {database}")
    logger.info(f"  Collection: {collection_name}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info("")

    # Create engine
    logger.info("Connecting to Cloud SQL...")
    engine_mgr = CloudSQLEngine(
        project_id=project_id,
        region=region,
        instance=instance,
        database=database,
    )

    try:
        # Test connection
        with engine_mgr.engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Connected to: {version}")

        # Execute migration
        executor = MigrationExecutor(
            engine=engine_mgr.engine,
            collection_name=collection_name,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        result = executor.execute()

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("Migration Summary")
        logger.info("=" * 70)

        for key, value in result.items():
            logger.info(f"  {key}: {value}")

        logger.info("=" * 70)

        if result["status"] == "success":
            logger.info("✅ Migration completed successfully!")
            return 0
        elif result["status"] == "warning":
            logger.warning("⚠️  Migration completed with warnings (check logs)")
            return 0
        elif result["status"] == "dry_run":
            logger.info("✅ Dry run completed successfully!")
            return 0
        else:
            logger.error("❌ Migration failed")
            return 1

    except MigrationError as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        engine_mgr.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
