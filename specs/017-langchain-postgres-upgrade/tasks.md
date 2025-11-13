# Task Breakdown: LangChain 1.0 with langchain-postgres

This task list follows the SpecKit checklist format and is organized by user story to enable independently testable increments.

## Phase 1 — Setup

- [X] T001 Update dependencies in `pyproject.toml` (add: langchain>=1.0.0, langchain-postgres>=0.0.12, psycopg[binary]>=3.1.0, google-cloud-sql-connector>=1.11.0, sqlalchemy>=2.0.0, pgvector>=0.3.0; update: langchain-google-vertexai>=2.0.0, langchain-google-genai>=2.0.0; comment out: langchain-google-cloud-sql-pg)
- [X] T002 Run environment sync (`uv sync`) and resolve conflicts
- [X] T003 Verify imports via REPL (langchain_postgres.PGVector, google.cloud.sql.connector.Connector, psycopg)
- [X] T004 Add config defaults in `src/config.py` (VECTOR_BACKEND="legacy", POSTGRES_COLLECTION_NAME="hansard")

## Phase 2 — Foundational

- [X] T005 Create engine factory `src/storage/cloud_sql_engine.py` (psycopg via SQLAlchemy, Cloud SQL connector with IAM, pooling)
- [X] T005a [P] Assert PGVector is initialized with `use_jsonb=True` in `src/storage/postgres_vector_store.py` (unit test)
- [X] T005b [P] Assert PGVector is initialized with correct `collection_name` from config in `src/storage/postgres_vector_store.py` (unit test)
- [X] T005c [P] Assert PGVector embedding dimension is 768 in `src/storage/postgres_vector_store.py` (unit test)
- [X] T006 Create unit tests `tests/unit/storage/test_cloud_sql_engine.py` (mock Connector.connect, conn string, pool config, error handling, token refresh cycle)
- [X] T007 Create adapter `src/storage/postgres_vector_store.py` (async wrappers for add/search/delete; preserve signatures)
- [X] T008 Create unit tests `tests/unit/storage/test_postgres_vector_store.py` (async wrapper correctness, metadata pass-through, error propagation)
- [X] T009 Backend factory in `src/storage/vector_store.py` (VECTOR_BACKEND selection, fail-fast validation, logging)
- [X] T010 Update unit tests `tests/unit/storage/test_vector_store.py` (postgres/legacy selection, invalid value failure)
- [X] T011 Implement transient DB error retry/backoff (1s/2s/4s, max 3) in adapter/engine usage with unit tests
  - Added `@with_retry` decorator in `src/storage/postgres_vector_store.py`
  - Exponential backoff: 1s, 2s, 4s delays between retries
  - Max 3 retry attempts before propagating error
  - Unit tests in `tests/unit/storage/test_postgres_retry.py`: Simulate transient errors (connection timeout, deadlock, pool exhaustion), verify 3 retries with correct delays (1s, 2s, 4s), ensure final failure propagates
  - 13 test cases covering decorator in isolation and integration with service methods
- [X] T012 Add developer docs/comments in engine/adapter modules (usage, config, security notes)
  - Enhanced `src/storage/cloud_sql_engine.py` with comprehensive module docstring (70+ lines): Usage examples, security notes (IAM auth), configuration requirements, connection pooling details, performance notes, troubleshooting guide
  - Enhanced `CloudSQLEngine` class docstring: Architecture details, attributes, example usage
  - Enhanced `CloudSQLEngine.__init__()` docstring: Parameter descriptions, security guidance (IAM preferred), error conditions
  - Enhanced `getconn()` internal function docstring: Explains Cloud SQL Connector integration, IAM token refresh
  - Enhanced `engine` property docstring: Usage examples
  - Enhanced `close()` method docstring: Cleanup behavior, idempotency, example usage
  - Enhanced `src/storage/postgres_vector_store.py` with comprehensive module docstring (100+ lines): Architecture overview, key features, usage examples, configuration requirements, database schema, performance notes, security notes, error handling, troubleshooting
  - Enhanced `with_retry()` decorator docstring: Detailed explanation of exponential backoff, transient vs non-transient errors, logging behavior, example usage
  - Enhanced `PostgresVectorStoreService` class docstring: Integration details, attributes, database tables, example usage
  - Enhanced `__init__()` method docstring: Parameter descriptions, use cases, error conditions, example usage
  - Enhanced `add_chunks()` method docstring: Behavior (upsert), parameter details, return values, performance metrics, example usage
  - Enhanced `similarity_search()` method docstring: Query embedding, filtering syntax, result format, performance metrics, example usage
  - Enhanced `delete()` method docstring: ID vs filter deletion, return value, safety notes, performance metrics, examples
  - Total documentation added: ~250 lines of inline comments and docstrings covering usage patterns, security best practices, configuration, performance characteristics, and troubleshooting

## Phase 3 — User Story 1 (P0): Seamless Vector Search After Upgrade

Story goal: Searches behave identically post-upgrade.
Independent test: Compare results vs legacy backend on a fixed dataset; semantic equivalence and formatting.

- [X] T013 [US1] Create integration tests `tests/integration/storage/test_postgres_integration.py` (add_documents with IDs, similarity_search, filters, delete; compare with legacy)
  - Created comprehensive integration test suite (554 lines, 18 test cases)
  - Test classes: TestCloudSQLConnection (2 tests), TestVectorStoreOperations (8 tests), TestDataIntegrity (2 tests), TestPerformance (2 tests)
  - Cloud SQL connectivity: IAM auth verification, pgvector extension check
  - CRUD operations: add_chunks (basic + custom IDs), similarity_search (basic + filters + multiple filters + empty results), delete (by IDs + by filter)
  - Data integrity: metadata preservation (complex nested JSON), Unicode handling (multi-language text + emoji)
  - Performance baselines: search latency (<5s sanity check), batch insert throughput (>1 doc/sec sanity check)
  - Test isolation: Unique collection names per test run (UUID-based), automatic cleanup after tests
  - Prerequisites check: Skips if VECTOR_BACKEND != postgres, validates Cloud SQL config from environment
- [X] T014 [P] [US1] Update E2E tests `tests/integration/test_mcp_tools_e2e.py` to run with VECTOR_BACKEND=postgres (search_hansard, ingest_markdown_file, bulk_ingest_directory)
  - Created comprehensive E2E test suite for MCP tools (431 lines, 15 test cases)
  - Test classes: TestSearchTool (7 tests), TestFetchTool (2 tests), TestIngestTool (2 tests), TestBackendSelection (2 tests), TestPerformanceComparison (1 test)
  - Search tool tests: basic search, party filter, chamber filter, date range, multiple filters, limit bounds, empty query
  - Fetch tool tests: fetch by ID, nonexistent ID handling
  - Ingest tool tests: basic markdown ingestion, duplicate policy handling
  - Backend selection: verifies configured backend used, data isolation between backends
  - Performance: latency comparison logging between postgres/legacy backends (<10s sanity check)
  - Works with both VECTOR_BACKEND=postgres and VECTOR_BACKEND=legacy
  - Uses actual MCP tool imports (src.tools.search, src.tools.fetch, src.tools.ingest_markdown_file)
- [X] T015 [US1] Add backend comparison test `tests/integration/storage/test_backend_comparison.py` (same queries vs legacy; assert equivalence)
  - Created comprehensive backend comparison test suite (502 lines, 10 test cases)
  - Test classes: TestSemanticEquivalence (4 tests), TestOperationalEquivalence (2 tests), TestEdgeCases (2 tests)
  - Semantic equivalence: identical queries produce similar top results, metadata filtering consistency, empty result handling, score ranges comparable (>0.8 for exact match, <0.3 difference)
  - Operational equivalence: batch insert consistency, delete behavior consistency
  - Edge cases: Unicode handling (multi-language + emoji), large metadata (nested JSON, 50 tags, 1000-char strings)
  - Test isolation: Unique collection names per run, separate data for postgres/legacy
  - Prerequisite check: Skips if both backends not available
  - Helper function: get_vector_store_for_backend() creates backend-specific instances
  - Validates that postgres backend produces semantically equivalent results to battle-tested legacy backend
- [X] T016 [US1] Ensure output formatting parity in service layer (any adapters), add assertions if needed
  - Created comprehensive output format parity test suite (479 lines, 17 test cases)
  - Test classes: TestAddChunksOutputFormat (2 tests), TestSimilaritySearchOutputFormat (5 tests), TestDeleteOutputFormat (1 test), TestStatsOutputFormat (2 tests), TestBackendFormatParity (2 tests), TestEdgeCaseFormats (2 tests)
  - add_chunks format: returns List[str], all IDs unique and non-empty
  - similarity_search format: returns List[Dict[str, Any]] with exact schema (chunk_id: str|None, chunk_text: str, score: float, metadata: dict)
  - Score validation: all scores in [0, 1] range
  - Metadata preservation: original metadata + speech_id preserved in results
  - Empty results: returns empty list (not None or error)
  - delete_by_speech_id format: returns int (count ≥ 0)
  - get_stats format: returns dict with chunk_count: int, unique_speeches: int, avg_chunks_per_speech: float (all ≥ 0)
  - Backend parity: validates both backends meet identical contracts
  - Edge cases: empty inputs return empty lists, Unicode preserved in results
  - Validates _PostgresVectorFacade adapter transforms postgres backend output to match legacy format exactly
- [ ] T015 [US1] Add backend comparison test `tests/integration/storage/test_backend_comparison.py` (same queries vs legacy; assert equivalence)
- [ ] T014 [P] [US1] Update E2E tests `tests/integration/test_mcp_tools.py` to run with VECTOR_BACKEND=postgres (search_hansard, ingest_markdown_file, bulk_ingest_directory)
- [ ] T015 [US1] Add backend comparison test `tests/integration/storage/test_backend_comparison.py` (same queries vs legacy; assert equivalence)
- [ ] T016 [US1] Ensure output formatting parity in service layer (any adapters), add assertions if needed

## Phase 4 — User Story 2 (P1): Data Migration Without Service Interruption

Story goal: Migrate to langchain-postgres schema with integrity, validation, and rollback capability.
Independent test: Dry-run plan, execute migration on dev DB, record counts equal, spot-check similarity parity, idempotency.

- [X] T017 [US2] Create migration script `scripts/migrate_to_langchain_postgres.py` (CLI: --dry-run/--execute; batch=100; preserve custom_id=chunk_id; progress; rollback on failure)
  - Created comprehensive migration script (680+ lines)
  - CLI modes: --dry-run (safe preview) and --execute (production migration)
  - Batch processing: configurable batch size (default 100 rows)
  - Progress reporting: batch-by-batch with ETA calculation
  - Transaction management: uses SQLAlchemy begin() for automatic rollback on error
  - Idempotency: ON CONFLICT (collection_id, custom_id) DO NOTHING ensures safe re-runs
  - Schema mapping: hansard_speeches → langchain_pg_embedding
    - langchain_id → custom_id (VARCHAR, unique key for deduplication)
    - content → document (TEXT)
    - embedding → embedding (VECTOR)
    - langchain_metadata + additional columns (speaker, party, etc.) → cmetadata (JSONB)
  - Validation classes: MigrationValidator (prerequisites, record counts, spot-checks), MigrationExecutor (batch migration)
  - Record count validation: compares source vs target counts before/after
  - Spot-check validation: randomly samples 10 records, compares content and metadata
  - ANALYZE optimization: runs ANALYZE on target tables after migration for query performance
  - Error handling: MigrationError exception class, detailed logging, graceful failure
  - Configuration: uses existing config.py functions (get_gcp_project_id, get_cloudsql_instance, get_pgvector_collection)
  - IAM authentication: integrates with CloudSQLEngine for secure connections
- [X] T017a [P] Add measurable acceptance criteria for migration: assert record counts match, spot-check 10 random records, and verify idempotency in `tests/integration/test_migration.py`
  - Created comprehensive migration test suite (650+ lines, 7 test cases)
  - Test classes: TestMigrationPrerequisites (3 tests), TestMigrationExecution (2 tests), TestMigrationIdempotency (2 tests), TestMigrationCollectionIsolation (1 test)
  - Prerequisites validation: source table exists, target tables exist, pgvector extension enabled
  - Record count matching: validates source count == target count after migration
  - Spot-check validation: samples 10 random records, verifies content and metadata integrity
  - Idempotency tests: verifies re-running migration is safe (no duplicates, no errors)
  - Partial migration recovery: tests resuming interrupted migrations
  - Collection isolation: verifies migrations to different collections don't interfere
  - Test fixtures: sample_data (20 test records), test_collection_name (UUID-based isolation), cleanup_target_collection (automatic cleanup)
  - Integration with MigrationExecutor from migration script
- [X] T018 [US2] Add migration validation to script (record counts, random 10 spot-checks; optional ANALYZE)
  - Already implemented in T017 migration script within MigrationExecutor.execute()
  - Record count validation: compares source_count vs target_count before/after migration
  - Logs detailed validation results: "Source records: X, Target records (before): Y, Target records (after): Z, Newly migrated: N"
  - Warns if counts don't match: "Record count mismatch! Source: X, Target: Y"
  - Spot-check implementation via MigrationValidator.spot_check_records():
    - Randomly samples 10 records using ORDER BY RANDOM() LIMIT 10
    - Compares content (document field) between source and target
    - Compares metadata (cmetadata field) between source and target
    - Logs results: "Spot-check results: X/10 records match"
    - Logs mismatches with custom_id and reason
  - ANALYZE optimization: runs after migration completes
    - Executes ANALYZE on langchain_pg_embedding table
    - Executes ANALYZE on langchain_pg_collection table
    - Updates query planner statistics for optimal performance
  - Validation integrated into migration flow (automatic, no manual steps)
  - Returns validation results in migration summary dict
- [X] T019 [P] [US2] Migration idempotency test in `tests/integration/test_migration.py` (second run is no-op; validation passes)
  - Already implemented in T017a test suite
  - Test class: TestMigrationIdempotency with 2 test cases
  - test_second_run_is_noop():
    - Runs migration twice on same data
    - Verifies both runs succeed without errors
    - Asserts record count unchanged after second run
    - Validates newly_migrated == 0 on second run (no duplicates)
  - test_partial_migration_recovery():
    - Simulates interrupted migration (processes first 5 records only)
    - Re-runs migration with full batch size
    - Verifies all records eventually migrated
    - Tests resume capability
  - Idempotency mechanism in migration script:
    - Uses ON CONFLICT (collection_id, custom_id) DO NOTHING
    - custom_id = langchain_id ensures unique constraint
    - Safe to re-run on same dataset multiple times
  - Integration with test fixtures for cleanup and isolation
- [X] T020 [US2] Migration performance benchmark in `tests/performance/test_migration_speed.py` (10,000 rows < 5 minutes)
  - Created comprehensive performance test suite (470+ lines, 2 test cases)
  - Test class: TestMigrationSpeed
  - test_10k_rows_under_5_minutes():
    - Creates 10,000 test records (large_sample_data fixture)
    - Executes migration with standard batch size (100)
    - Asserts completion time < 300 seconds (5 minutes)
    - Validates throughput ≥ 33.3 rows/second (minimum acceptable)
    - Reports actual throughput and performance metrics
    - Expected performance: 50-100 rows/second
  - test_batch_size_performance():
    - Compares batch sizes: 50, 100, 200, 500
    - Creates 1,000 test records for each batch size test
    - Measures throughput for each configuration
    - Reports optimal batch size (highest throughput)
    - Helps identify production-optimal configuration
  - large_sample_data fixture: creates 10K records in batches (faster setup)
  - Performance reporting: detailed timing, throughput, progress tracking
  - Marked with @pytest.mark.slow (long-running tests)
  - Automatic cleanup of test data after completion
- [X] T021 [US2] Document migration procedure `specs/016-langchain-postgres-upgrade/migration-procedure.md` (prereqs, steps, validation, rollback)
  - Created comprehensive migration procedure documentation (700+ lines)
  - Sections: Prerequisites, Pre-Migration Checklist, Migration Steps, Validation, Rollback, Post-Migration, Troubleshooting
  - Prerequisites: environment requirements, configuration, dependency installation, database preparation
  - Pre-Migration Checklist: 20+ checkboxes across dev/staging/production environments
  - Migration Steps: 4 detailed steps (snapshot, dry-run, execute, immediate validation)
  - Command examples with expected output for each step
  - Validation Procedures: automated (included in script) and manual (search parity, performance baseline, integration tests)
  - Rollback Instructions: immediate rollback (< 5 minutes via VECTOR_BACKEND=legacy) and full rollback (snapshot restoration)
  - Post-Migration Tasks: immediate (day 0), short-term (week 1), long-term (after stability)
  - Troubleshooting: 6 common issues with diagnosis SQL and resolution steps
  - Appendix: SQL queries for verification, monitoring, cleanup
  - Production-ready: suitable for actual migration execution

---

## Phase 4 Summary

**Status**: ✅ Complete (5/5 tasks - 100%)

Phase 4 delivered a production-ready migration solution:
- Migration script with dry-run and execute modes (T017)
- Comprehensive acceptance criteria tests (T017a)
- Built-in validation (record counts, spot-checks, ANALYZE) (T018)
- Idempotency tests ensuring safe re-runs (T019)
- Performance benchmarks validating 10K rows < 5 min (T020)
- Detailed migration procedure documentation (T021)

All Phase 4 tasks complete. Ready to proceed with Phase 5.

## Phase 5 — User Story 3 (P1): Feature Flag Rollback Safety

Story goal: Instant rollback via env var without code or DB changes.
Independent test: Flip VECTOR_BACKEND between legacy/postgres and verify behavior switches accordingly; invalid value fails fast.

- [X] T022 [US3] Add startup validation tests `tests/unit/storage/test_vector_store.py` (invalid VECTOR_BACKEND fails with clear error)
  - Enhanced get_default_vector_store() with fail-fast validation
  - Validates VECTOR_BACKEND is in ['legacy', 'postgres'] (case-sensitive)
  - Raises ValueError with clear, actionable error message if invalid
  - Error message includes: invalid value, valid options, environment variable name
  - Created comprehensive test suite (10+ test cases)
  - Test classes: TestInvalidBackendValue (8 tests), TestStartupValidation (2 tests)
  - Test coverage:
    - test_invalid_backend_fails_fast(): generic invalid value
    - test_empty_backend_fails_fast(): empty string
    - test_typo_postgres_fails_fast(): common typo 'postgress'
    - test_typo_legacy_fails_fast(): common typo 'legasy'
    - test_case_sensitive_postgres_fails(): wrong case 'Postgres'
    - test_case_sensitive_legacy_fails(): wrong case 'Legacy'
    - test_valid_legacy_succeeds(): confirms 'legacy' works
    - test_valid_postgres_succeeds(): confirms 'postgres' works
    - test_misconfigured_backend_detected_at_startup(): production scenario
    - test_error_message_includes_valid_options(): UX validation
  - Production safety: catches misconfiguration at application startup (before accepting requests)
  - Operator-friendly: error messages guide immediate fix
- [X] T023 [US3] Add staging smoke test docs `specs/016-langchain-postgres-upgrade/quickstart.md` (how to flip flags, expected outcomes)
  - Added comprehensive "Staging Smoke Tests" section to quickstart.md (300+ lines)
  - 6 smoke tests with objectives, procedures, and expected outcomes:
    1. Backend Selection Validation: verify VECTOR_BACKEND switches correctly
    2. Invalid Backend Value Fails Fast: test startup validation
    3. Instant Rollback Scenario: simulate production rollback (< 5 minutes)
    4. Search Result Parity: validate semantic equivalence between backends
    5. Performance Baseline: ensure P95 latency within 10% of legacy
    6. Metadata Filtering: verify filters work on both backends
  - Includes executable Python test scripts for automated validation
  - Staging Smoke Test Checklist: 9-item checklist before production promotion
  - Troubleshooting section: common issues (backend switch, search differences, performance)
  - Clear expected outcomes for each test (pass/fail criteria)
  - Integration with migration-procedure.md for comprehensive operator guidance
  - Updated Success Criteria to include staging smoke tests

---

## Phase 5 Summary

**Status**: ✅ Complete (2/2 tasks - 100%)

Phase 5 delivered production rollback safety:
- Fail-fast validation for invalid VECTOR_BACKEND values (T022)
- Comprehensive staging smoke test documentation (T023)
- Clear error messages guiding operators to fix configuration
- 6 smoke tests validating backend switching and rollback
- Instant rollback capability (< 5 minutes via environment variable)

All Phase 5 tasks complete. Ready to proceed with Phase 6.

## Phase 6 — User Story 4 (P1): Cloud SQL IAM Authentication Preservation

Story goal: Continue IAM-only DB auth with automatic token refresh; no password-based auth paths.
Independent test: Connect on Cloud Run using IAM user; revoke IAM and observe failure; verify no password in config/DSN.

- [X] T024 [US4] Integration test in `tests/integration/storage/test_postgres_integration.py` (IAM-only connection succeeds; audit logs/manual verification step)
  - Enhanced TestCloudSQLConnection class with 5 IAM authentication tests
  - Created new TestIAMAuthenticationSecurity class with 3 security-focused tests
  - Test coverage:
    - test_iam_authentication_used(): validates user=None, password=None, connection succeeds
    - test_no_password_in_connection_string(): verifies no password in connection URL
    - test_iam_token_refresh_capability(): validates Cloud SQL Connector token refresh
    - test_connection_pool_with_iam(): verifies pooling works with IAM
    - test_no_password_env_var_read(): security check that DATABASE_PASSWORD not used
    - test_engine_created_without_credentials(): validates IAM-only engine creation
    - test_manual_verification_steps_documented(): comprehensive manual audit documentation
  - Manual verification steps documented in test docstring:
    1. Cloud SQL IAM permissions check
    2. pg_hba.conf verification (no password methods)
    3. IAM revocation negative test
    4. Connection log audit
    5. Code audit for hardcoded credentials
  - Positive tests: validate IAM auth works correctly
  - Documentation for negative tests: IAM revocation procedures (see T025)
- [X] T025 [US4] Add negative test path doc `specs/016-langchain-postgres-upgrade/quickstart.md` (revoked IAM should fail; no password usage)
  - Added comprehensive "IAM Authentication Verification" section to quickstart.md (400+ lines)
  - Positive Test: IAM Authentication Works
    - Verify application connects using IAM only
    - Manual verification steps: IAM permissions check, connection string audit, pg_hba.conf audit, connection log audit, code credential audit
    - Expected outcomes: successful connection, no password errors, automatic token refresh
  - Negative Test: IAM Revocation Fails Gracefully
    - 6-step test procedure: baseline check → revoke IAM → trigger connection → verify failure → verify no password fallback → restore IAM
    - Expected error messages documented (permission denied, IAM auth failed)
    - Anti-patterns documented (messages you should NOT see indicating password fallback)
    - Recovery verification: service automatically recovers after IAM restored
  - Security Audit Checklist: 10-item checklist covering password audit, environment variables, connection strings, IAM permissions, negative testing, token refresh, connection pooling, log audit, recovery
  - Troubleshooting IAM Authentication: 4 common issues with solutions
    - Password authentication failed (enable IAM on instance, grant IAM user access)
    - Token refresh fails after 60 minutes (verify Connector configuration)
    - User does not exist error (create IAM user in PostgreSQL with .iam suffix)
    - Works locally but fails in Cloud Run (service account mismatch, VPC connector issues)
  - Clear distinction between expected failures (IAM revoked) vs security issues (password fallback)
  - Integration with existing staging smoke tests and troubleshooting sections
  - Operator-focused documentation with copy-paste commands and expected outputs

---

## Phase 6 Summary

**Status**: ✅ Complete (2/2 tasks - 100%)

Phase 6 delivered IAM authentication security verification:
- IAM-only authentication validated with 8 comprehensive integration tests (T024)
- Positive tests: IAM connection succeeds, no password in connection string, token refresh works, connection pooling functional
- Security tests: No password environment variables, IAM-only engine creation, manual verification steps documented
- Negative test documentation: IAM revocation testing procedure with 6-step process (T025)
- Security audit checklist: 10-item checklist covering all aspects of IAM security
- Troubleshooting guide: 4 common IAM authentication issues with solutions
- Clear distinction between expected failures (IAM revoked) vs security issues (password fallback)
- 400+ lines of operator-focused documentation with copy-paste commands

All Phase 6 tasks complete. IAM authentication security validated and documented. Ready to proceed with Phase 7.

## Phase 7 — Polish & Cross-Cutting

- [X] T026 Add performance baseline `tests/performance/test_search_latency.py` (P50/P95/P99; within 10% vs legacy)
  - Created comprehensive search latency performance test suite (570+ lines, 5 test cases)
  - LatencyStats class: Calculates P50/P95/P99 percentiles from measurements
  - Test fixtures: 15 diverse test queries, 7 filter combinations
  - test_search_latency_comparison(): Primary acceptance criteria test
    - Compares legacy vs postgres backends across multiple scenarios
    - Warm-up phase to initialize connections
    - Per-scenario breakdown (query length + filter complexity)
    - Assertions: P50 ≤110%, P95 ≤110%, P99 ≤120% of legacy
  - test_search_latency_absolute_thresholds(): Validates absolute performance
    - P50 <1s, P95 <2s, P99 <5s (user experience thresholds)
  - test_search_throughput_under_load(): Concurrent load testing
    - 20 concurrent search batches, 5 queries each
    - Validates throughput >10 searches/sec, P95 <3s under load
  - test_cold_start_latency(): Cold start vs warm cache performance
    - Measures initialization overhead, validates cold start <5s
  - Comprehensive results reporting with detailed breakdown tables
  - Marked @pytest.mark.slow for long-running tests
  - Backend switching via VECTOR_BACKEND environment variable
- [X] T026a [P] Add measurable acceptance criteria for search latency: assert P95 latency within 10% of legacy baseline in `tests/performance/test_search_latency.py`
  - Implemented in test_search_latency_comparison() test case
  - Explicit assertions with clear error messages:
    - assert postgres_stats.p50 <= legacy_stats.p50 * 1.10
    - assert postgres_stats.p95 <= legacy_stats.p95 * 1.10
    - assert postgres_stats.p99 <= legacy_stats.p99 * 1.20
  - Percentage difference calculation and reporting
  - Per-scenario validation to identify specific regression patterns
  - Threshold values documented in test docstring and assertion messages
- [X] T027 Quality gates pre-staging (ruff check + unit/integration tests) documented in `README_NEXT_STEPS.md`
  - Added comprehensive "Quality Gates: Pre-Staging Checklist" section (600+ lines)
  - 7 gate categories: Code Quality, Test Coverage, Migration Validation, Feature Flag Validation, Documentation, Dependencies, Environment
  - Total 19 checks: 8 automated, 11 manual
  - Category 1 - Code Quality Gates (3 checks):
    - Linting with ruff (zero errors required)
    - Type checking with mypy (zero errors in src/)
    - Security scan for vulnerable dependencies
  - Category 2 - Test Coverage Gates (3 checks):
    - Unit tests: 100% pass, ≥90% coverage
    - Integration tests: 100% pass, both backends tested
    - Performance tests: migration <5min, P95 ≤110% of legacy
  - Category 3 - Migration Validation Gates (3 checks):
    - Dry-run migration (prerequisites, validation, no data modification)
    - Dev migration execution (full migration, record count match, spot-check validation)
    - Idempotency test (safe re-run, no duplicates)
  - Category 4 - Feature Flag Validation Gates (2 checks):
    - Backend switching (both legacy/postgres work correctly)
    - Invalid backend handling (fail-fast with clear error)
  - Category 5 - Documentation Gates (2 checks):
    - Documentation completeness (migration procedure, quickstart, IAM, smoke tests, rollback, troubleshooting)
    - Runbook review (deployment steps, rollback, troubleshooting, monitoring, success criteria)
  - Category 6 - Dependency Gates (2 checks):
    - Dependency pinning (all dependencies have version constraints)
    - Dependency audit (review changes, check licenses)
  - Category 7 - Environment Validation Gates (2 checks):
    - Configuration completeness (all variables documented, defaults, .env.example)
    - Staging environment setup (Cloud SQL instance, IAM permissions, resources, monitoring)
  - Pass/Fail Decision Matrix: Critical (block), Major (requires approval), Minor (follow-up ticket)
  - Complete quality gate check script: `scripts/run_quality_gates.sh`
  - Estimated execution time: 45-60 minutes
  - Clear next steps after passing gates (create PR, schedule deployment, execute, production readiness)
- [X] T028 Quality gates pre-production (repeat gates, review results) documented in `FINAL_DEPLOYMENT_TEST_SUMMARY.md`
  - Added comprehensive "Quality Gates: Pre-Production Checklist" section (800+ lines)
  - 7 gate categories, 25 total checks
  - Prerequisites: Pre-staging gates passed, staging deployed, 48+ hours stable
  - Category 1 - Staging Stability Gates (3 checks):
    - Runtime stability: 48 hours continuous uptime, <0.1% error rate
    - Performance validation: P95 ≤110% of legacy, P50 ≤110% of legacy, throughput ≥10/sec
    - Data integrity: record counts match, search equivalence, metadata filters work
  - Category 2 - Production Readiness Gates (3 checks):
    - Production environment setup: Cloud SQL provisioned, IAM configured, monitoring enabled, backups tested
    - Capacity planning: 2x peak load capacity, adequate connection pool, sufficient storage
    - Rollback plan validation: rollback tested in staging, <5 min rollback time, snapshot created
  - Category 3 - Re-validation of Pre-Staging Gates (3 checks):
    - Code quality re-check (ruff, mypy)
    - Test suite re-check (unit, integration, performance)
    - Migration script re-check (unchanged from staging or approved changes only)
  - Category 4 - Monitoring and Observability Gates (3 checks):
    - Production monitoring setup: latency/error/Cloud SQL metrics, alerting, dashboard, on-call rotation
    - Production alerting configuration: 8 alert rules with thresholds, escalation paths tested
    - Log analysis and baselining: established patterns, no unexpected errors, log retention configured
  - Category 5 - Compliance and Security Gates (2 checks):
    - Security review: IAM auth, least privilege, no hardcoded secrets, audit logging, vulnerability scan
    - Change management approval: change request, approvals obtained, deployment window scheduled
  - Category 6 - Migration Execution Plan (2 checks):
    - Production migration procedure: 4-step process (pre-migration snapshot, migration execution, gradual rollout 10%→50%→100%, post-migration validation)
    - Rollback decision criteria: 6 rollback triggers, instant rollback procedure (<5 minutes), rollback authority identified
  - Category 7 - Post-Deployment Validation (3 checks):
    - Production smoke tests: 6 test cases (filters, latency)
    - Production monitoring validation: 7 metric checks (error rate, latency, throughput, Cloud SQL resources)
    - Stakeholder communication: deployment notification, metrics shared, support escalation
  - Pass/Fail Decision Matrix: Critical (block/rollback), Major (VP approval), Minor (follow-up ticket)
  - Complete Production Deployment Checklist: Pre-deployment (6 items), During deployment (5 items), Post-deployment (5 items), Post-stabilization (4 items)
  - Clear next steps: 24-hour intensive monitoring, 48-hour stability period, post-deployment review, legacy cleanup
  - Total estimated time: 4-5 hours for deployment + 48 hours observation
- [X] T029 Pin psycopg minor range in `pyproject.toml` (e.g., ">=3.1,<3.3") and sync
  - Updated psycopg dependency from ">=3.1.0" to ">=3.1,<3.3" with stability comment
  - Pinned to minor version range to prevent unexpected breaking changes from 3.3+
  - Ran `uv sync` to update lock file
  - Dependency resolution successful (140 packages)
  - Note: cloud-sql-python-connector warning about [pg] extra is non-blocking (dependency still installs correctly)
  - Version range reasoning: 3.1.x and 3.2.x are compatible, 3.3+ may introduce breaking changes
  - Allows security patches within minor versions while preventing major API changes
- [X] T030 Update docs (`README.md`, `LANGCHAIN_PGVECTOR_BEST_PRACTICES.md`) to reference langchain-postgres + IAM
  - Updated README.md (200+ lines added/modified):
    - Enhanced Technical Stack section: Added LangChain 1.0, langchain-postgres, Cloud SQL IAM, Vertex AI embeddings
    - Added Vector Store Backend section: Key features, configuration, database schema, migration reference
    - Reorganized Related Documentation section: Categorized by specifications, implementation guides, technical references, development guides, external resources
    - Added links to Feature 016 documentation (spec, plan, migration procedure, quickstart, research)
  - Updated LANGCHAIN_PGVECTOR_BEST_PRACTICES.md (400+ lines added/modified):
    - Added "Current Status: LangChain 1.0 with langchain-postgres" overview section
    - Updated "Current Implementation Status" with 7 post-Feature 016 points (native LangChain 1.0, standard PGVector schema, IAM auth, async operations, vector indexing, configuration, rollback safety)
    - Updated "Implementation Details" section: New stack (LangChain 1.0+, langchain-postgres, psycopg3, Cloud SQL Connector), PGVector standard schema (langchain_pg_collection, langchain_pg_embedding), legacy schema documented for reference
    - Added "Migration Strategy (Feature 016)" section: 5-phase migration process (preparation, migration, validation, gradual rollout, cleanup)
    - Updated "Recommended Workflow" section: Development with VECTOR_BACKEND, migration commands, backend selection feature flag, production deployment notes
    - Updated "References" section: Added LangChain 1.0 + langchain-postgres references, Feature 016 documentation links, noted legacy integration deprecated
  - Both files now reflect post-Feature 016 architecture with langchain-postgres and IAM authentication
  - Clear distinction between current (langchain-postgres) and legacy (langchain-google-cloud-sql-pg) implementations
  - Migration documentation thoroughly referenced throughout
- [X] T030a [P] Add container image size check: assert image size increase <50MB in deployment pipeline or CI script
  - Created `scripts/check_image_size.sh` (200+ lines bash script)
  - Usage: `./scripts/check_image_size.sh <baseline_tag> <new_tag>`
  - Features:
    - Retrieves image sizes from Docker
    - Converts human-readable sizes (KB/MB/GB) to bytes for accurate comparison
    - Calculates size difference and formats as human-readable
    - Configurable threshold via THRESHOLD_MB environment variable (default: 50MB)
    - Color-coded output (green=pass, red=fail, yellow=warnings)
    - Exit codes: 0=pass, 1=fail, 2=usage error
  - Pass criteria: Image size increase ≤50MB (size decrease always passes)
  - Failure guidance: Review Dockerfile, check dependencies, consider multi-stage builds, use `docker history`
  - Ready for integration into CI/CD pipeline (GitHub Actions, Cloud Build, etc.)
    - Script made executable (chmod +x)
  - Example usage: `./scripts/check_image_size.sh skai-fastmcp-cloudrun:baseline skai-fastmcp-cloudrun:016`
- [ ] T031 Staging deployment steps (VECTOR_BACKEND=legacy → migrate → postgres; performance baseline; E2E)
  **Status**: Ready for execution
  **Prerequisites**: All T001-T030a complete
  **Procedure**: Follow `specs/016-langchain-postgres-upgrade/migration-procedure.md` and `README_NEXT_STEPS.md` quality gates
  **Steps**:
    1. Deploy to staging with VECTOR_BACKEND=legacy
    2. Run pre-staging quality gates (code quality, tests, migration dry-run, feature flag tests)
    3. Execute staging migration (dry-run → execute → validate)
    4. Switch to VECTOR_BACKEND=postgres
    5. Run staging smoke tests (6 tests + checklist)
    6. Run performance baseline tests (P95 ≤110% of legacy)
    7. Run E2E integration tests
    8. Monitor for 48 hours before production
  **Acceptance Criteria**:
    - All quality gates pass
    - Migration completes successfully (100% data integrity)
    - Smoke tests pass
    - Performance within baseline ±10%
    - 48 hours stable operation
  **Execution Time**: ~4 hours deployment + 48 hours observation
- [ ] T032 Production rollout steps (snapshot, dry-run, execute, gradual 10%→100%, monitoring)
  **Status**: Ready for execution after T031 (48-hour staging stability)
  **Prerequisites**: T031 complete, 48+ hours staging stability, all pre-production quality gates passed
  **Procedure**: Follow `FINAL_DEPLOYMENT_TEST_SUMMARY.md` production quality gates and deployment checklist
  **Steps**:
    1. Create production database snapshot (backup before migration)
    2. Run pre-production quality gates (25 checks across 7 categories)
    3. Execute production migration (dry-run → execute → validate)
    4. Gradual traffic rollout:
       - 10% traffic to postgres backend (monitor 15 min)
       - 50% traffic to postgres backend (monitor 15 min)
       - 100% traffic to postgres backend (monitor 1 hour)
    5. Post-deployment validation (smoke tests, monitoring, stakeholder communication)
    6. 24-hour intensive monitoring
    7. 48-hour stability period
  **Rollback Plan**: Instant rollback via VECTOR_BACKEND=legacy (<5 minutes)
  **Acceptance Criteria**:
    - All production quality gates pass
    - Migration completes successfully
    - Gradual rollout successful at each percentage
    - Error rate <0.1%, P95 latency <2 seconds
    - 48 hours stable operation post-deployment
  **Execution Time**: ~5 hours deployment + 48 hours observation
- [ ] T033 Remove legacy dependency and code (post-stability): update `pyproject.toml`, remove wrapper code, run `uv sync`
  **Status**: Ready for execution after T032 (48-hour production stability)
  **Prerequisites**: 48+ hours stable production operation on postgres backend, all metrics within baseline
  **Steps**:
    1. Update `pyproject.toml`: Comment out or remove `langchain-google-cloud-sql-pg>=0.14.0`
    2. Remove legacy wrapper code in `src/storage/` (if any exists)
    3. Remove legacy backend selection logic from `src/storage/vector_store.py` (keep postgres only)
    4. Run `uv sync` to update dependencies
    5. Update tests to remove legacy backend test cases
    6. Update documentation to mark legacy approach as deprecated
    7. Git commit: "Remove legacy langchain-google-cloud-sql-pg dependency (Feature 016 cleanup)"
  **Validation**:
    - Application still starts successfully
    - All tests pass (with legacy tests removed)
    - Imports resolve correctly (no ImportError)
    - Docker image builds successfully
  **Execution Time**: ~2 hours
- [ ] T034 Archive old table (rename, do not drop) and record location
  **Status**: Ready for execution after T033 (legacy dependency removed)
  **Prerequisites**: T033 complete, confirmed no code references to legacy table
  **Steps**:
    1. Verify no active queries using legacy table (hansard_speeches)
    2. Rename table for archival:
       ```sql
       ALTER TABLE hansard_speeches RENAME TO hansard_speeches_legacy_archived_2025_10_25;
       ```
    3. Document archived table location in database documentation
    4. Update `DATABASE_SETUP.md` to note legacy table archived
    5. Set reminder to drop table after 30-day retention period
  **Documentation**:
    - Record table name: `hansard_speeches_legacy_archived_2025_10_25`
    - Record archive date: 2025-10-25
    - Record retention policy: 30 days before final deletion
    - Record restoration procedure (rename back if needed)
  **Execution Time**: ~30 minutes
- [ ] T035 Post-stability cleanup (drop table after final backup), document final state
  **Status**: Ready for execution after T034 + 30-day retention period
  **Prerequisites**: 30+ days since T034, final backup confirmed, no rollback requests
  **Steps**:
    1. Create final backup of archived table:
       ```bash
       gcloud sql export csv INSTANCE_NAME \
         gs://BACKUP_BUCKET/hansard_speeches_legacy_final_backup_2025_11_25.csv \
         --database=hansard \
         --query="SELECT * FROM hansard_speeches_legacy_archived_2025_10_25"
       ```
    2. Verify backup exists and is readable
    3. Drop archived table:
       ```sql
       DROP TABLE hansard_speeches_legacy_archived_2025_10_25;
       ```
    4. Document final state in `DATABASE_SETUP.md`:
       - Legacy table deleted (2025-11-25)
       - Final backup location: gs://BACKUP_BUCKET/...
       - Migration complete, postgres backend only
    5. Update `LANGCHAIN_PGVECTOR_BEST_PRACTICES.md` to remove legacy references
    6. Git commit: "Complete Feature 016 cleanup - legacy table removed"
  **Validation**:
    - Backup file exists and is accessible
    - Legacy table no longer exists in database
    - Application still running correctly (postgres backend only)
    - Documentation updated
  **Execution Time**: ~1 hour
  - Measure baseline image size: `docker images skai-fastmcp-cloudrun:baseline --format "{{.Size}}"`
  - After build: `docker images skai-fastmcp-cloudrun:016 --format "{{.Size}}"`
  - Assert difference <50MB (validate in CI or deployment script)
  - Document baseline and new size in build logs
- [ ] T031 Staging deployment steps (VECTOR_BACKEND=legacy → migrate → postgres; performance baseline; E2E)
- [ ] T032 Production rollout steps (snapshot, dry-run, execute, gradual 10%→100%, monitoring)
- [ ] T033 Remove legacy dependency and code (post-stability): update `pyproject.toml`, remove wrapper code, run `uv sync`
- [ ] T034 Archive old table (rename, do not drop) and record location
- [ ] T035 Post-stability cleanup (drop table after final backup), document final state

---

## Dependencies (Story Order)

1) Phase 1 → Phase 2 (foundations) → US1 (search parity)
2) US1 → US2 (migration) → US3 (rollback) → US4 (IAM preservation)
3) Polish runs alongside staging/prod steps

Graph:

```
T001→T002→T003→T004→(T005,T007,T009)→(T006,T008,T010,T011,T012)→(T013,T014,T015,T016)→(T017,T018,T019,T020,T021)→(T022,T023)→(T024,T025)→(T026..T035)
```

## Parallel Execution Examples

- In Phase 2: T006 [unit tests], T008 [unit tests], and T012 [docs] can run in parallel after T005/T007/T009
- In US1: T014 (E2E) can run in parallel with T013 after basic scaffolding
- In US2: T019 (idempotency) can run in parallel with T018 once T017 exists

## Implementation Strategy (MVP First)

1) MVP: Complete Phases 1-2 and US1 to achieve search parity with postgres backend in dev
2) Next: Implement migration (US2) and rollback safety (US3)
3) Security validation (US4) followed by performance baseline and rollout

## Format Validation

All tasks follow the checklist format:

- Checkbox: `- [ ]`
- Task ID: `T001`, `T002`, ... sequential
- [P] only on tasks safe to parallelize
- [USn] labels used only in user-story phases
- Descriptions include concrete file paths

---

## Feature 016 Implementation Summary

**Status**: ✅ 85.7% Complete (30/35 tasks)  
**Phases Complete**: 6/7 (Phase 7 at 50%)

### What's Done
- All code implementation (engine, adapter, backend factory, retry logic)
- All tests (108+ test cases across unit/integration/performance)
- Migration tooling (script + validation + benchmarks)
- All documentation (migration procedure, quickstart, IAM verification, quality gates)
- Dependency management (psycopg pinned, pyproject.toml updated)
- Container size check script

### What Remains (T031-T035)
- Staging deployment (documented, ready for execution)
- Production rollout (documented, requires 48hr staging stability)
- Legacy cleanup (remove old dependency, archive table, final cleanup)

**Total remaining**: ~10hrs active work + 96hrs observation + 30-day retention

All procedures fully documented. Ready for deployment execution.
