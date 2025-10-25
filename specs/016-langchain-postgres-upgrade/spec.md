# Feature Specification: LangChain 1.0 with langchain-postgres

**Feature Branch**: `016-langchain-postgres-upgrade`
**Created**: 2025-10-25
**Status**: Draft
**Input**: Upgrade to LangChain 1.0+ using the dedicated `langchain-postgres` package (not langchain-community) with Cloud SQL IAM authentication via `google-cloud-sql-connector` and psycopg3 driver. Replace blocking `langchain-google-cloud-sql-pg` dependency that requires `langchain-core<1.0.0`. Maintain full backward compatibility with existing vector search functionality, Cloud SQL PostgreSQL with pgvector extension, and all current MCP tools. Requires data migration to langchain-postgres standard schema (langchain_pg_collection, langchain_pg_embedding tables).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless Vector Search After Upgrade (Priority: P0)

A Claude Desktop user with existing Hansard data indexed in the database continues using the `search_hansard` MCP tool after the LangChain 1.0 upgrade. The search functionality works identically to before the upgrade, returning the same quality and format of results.

**Why this priority**: This is the critical success criterion - no regression in user-facing functionality. If search breaks or degrades, the upgrade fails regardless of internal improvements.

**Independent Test**: Can be tested by running the same search queries before and after upgrade and comparing results for semantic equivalence and quality.

**Acceptance Scenarios**:

1. **Given** existing Hansard data in the database, **When** user searches for "climate change policy" after upgrade, **Then** results match the quality and relevance of pre-upgrade searches
2. **Given** a search query with metadata filters (e.g., date range, speaker), **When** user executes filtered search post-upgrade, **Then** filtering works identically to pre-upgrade behavior
3. **Given** multiple concurrent search requests from different MCP clients, **When** upgrade is deployed, **Then** all searches complete successfully without conflicts or errors

---

### User Story 2 - Data Migration Without Service Interruption (Priority: P1)

A system administrator needs to migrate existing vector embeddings from the current table schema to the new langchain-postgres schema. The migration must preserve all data integrity, verify successful migration before cutover, and provide rollback capability if issues are detected.

**Why this priority**: Without successful migration, the upgrade cannot proceed to production. This is the technical foundation that enables the P0 scenario.

**Independent Test**: Can be tested by running migration script against development database, verifying record counts match, and spot-checking search result parity.

**Acceptance Scenarios**:

1. **Given** existing hansard_speeches table with 1000 records, **When** administrator runs migration with --dry-run flag, **Then** migration plan shows exactly what will be migrated without modifying data
2. **Given** migration dry-run shows no errors, **When** administrator executes migration with --execute flag, **Then** all 1000 records appear in langchain_pg_embedding table with preserved metadata
3. **Given** migration completed successfully, **When** administrator runs validation queries comparing old vs new schema, **Then** vector search results show equivalent similarity scores and rankings
4. **Given** migration encounters an error at record 500 of 1000, **When** error is detected, **Then** migration stops gracefully, logs detailed error, and leaves data in consistent state for retry

---

### User Story 3 - Feature Flag Rollback Safety (Priority: P1)

A system administrator deploying the LangChain 1.0 upgrade to production discovers an edge case issue. They need to immediately rollback to the previous langchain-google-cloud-sql-pg implementation by changing an environment variable, without code deployment or database changes.

**Why this priority**: Essential for safe production rollout. Provides escape hatch if unexpected issues arise, enabling quick recovery while investigation proceeds.

**Independent Test**: Can be tested by deploying with new backend, switching VECTOR_BACKEND environment variable to "legacy", and verifying system uses old implementation without errors.

**Acceptance Scenarios**:

1. **Given** service deployed with VECTOR_BACKEND=postgres, **When** administrator sets VECTOR_BACKEND=legacy and restarts service, **Then** service uses old langchain-google-cloud-sql-pg without errors
2. **Given** service running with legacy backend, **When** administrator switches to VECTOR_BACKEND=postgres, **Then** service uses new langchain-postgres backend and searches work correctly
3. **Given** VECTOR_BACKEND is set to invalid value, **When** service starts, **Then** startup fails with clear error message indicating valid options

---

### User Story 4 - Cloud SQL IAM Authentication Preservation (Priority: P1)

A Cloud Run service deployed with IAM database authentication continues authenticating to Cloud SQL PostgreSQL using the service account's IAM credentials after the LangChain 1.0 upgrade. No password-based authentication is introduced.

**Why this priority**: Security requirement - current IAM authentication provides superior security (no password management, automatic token rotation, integrated audit logging). Regression to password auth would be a security downgrade.

**Independent Test**: Can be tested by deploying to Cloud Run with IAM-only database user, verifying connection succeeds, and checking database logs show IAM authentication.

**Acceptance Scenarios**:

1. **Given** Cloud SQL user configured with IAM authentication only (no password), **When** Cloud Run service connects to database, **Then** connection succeeds using service account IAM credentials
2. **Given** service running on Cloud Run, **When** database connection is established, **Then** Cloud SQL audit logs show authentication via IAM principal, not password
3. **Given** service account IAM permissions are revoked, **When** service attempts database connection, **Then** connection fails with clear IAM permission error

---

### Edge Cases

- What happens when langchain-postgres schema changes in future versions (migration path)?
- How does system handle partial migration (some records migrated, some not)?
- What happens if administrator runs migration script twice?
- How are extremely large embeddings (edge case vector dimensions) handled in new schema?
- What happens when new code tries to connect but migration hasn't been run yet?
- How does system behave when VECTOR_BACKEND is set but corresponding implementation is unavailable?
- What happens during schema table creation if permissions are insufficient?
- How are connection pool exhaustion scenarios handled with new connector?
- What happens when psycopg3 has breaking API changes in minor versions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST upgrade to langchain>=1.0.0, langchain-postgres>=0.0.12, and psycopg>=3.0 while maintaining all current vector search functionality
- **FR-002**: System MUST replace langchain-google-cloud-sql-pg dependency with langchain-postgres + google-cloud-sql-connector combination
- **FR-003**: System MUST implement Cloud SQL IAM authentication using google-cloud-sql-connector with automatic token management
- **FR-004**: System MUST use psycopg3 driver (postgresql+psycopg:// connection string format) for all database connections
- **FR-005**: System MUST provide data migration script that converts existing table schema to langchain-postgres standard schema (langchain_pg_collection, langchain_pg_embedding tables)
- **FR-006**: System MUST implement VECTOR_BACKEND environment variable with values "postgres" (new) and "legacy" (fallback) for gradual rollout
- **FR-007**: System MUST preserve all existing metadata fields during migration and ensure metadata filtering works identically post-upgrade
- **FR-008**: System MUST support explicit document IDs in add_documents() to maintain chunk_id continuity
- **FR-009**: System MUST implement async wrapper layer (asyncio.to_thread) around langchain-postgres synchronous operations to maintain async VectorStoreService API
- **FR-010**: System MUST maintain backward compatibility with all existing MCP tools (search_hansard, ingest_markdown_file, bulk_ingest_directory)

### Non-Functional Requirements

- **NFR-001**: Vector search latency MUST NOT increase by more than 10% compared to pre-upgrade baseline (P95 response time)
- **NFR-002**: Database connection pool MUST be reused across requests to avoid connection overhead (SQLAlchemy engine pooling)
- **NFR-003**: Migration script MUST process 10,000 records in under 5 minutes on standard Cloud SQL instance (db-custom-1-3840 or equivalent; actual target should be validated against production instance specifications)
- **NFR-004**: System MUST log detailed connection information at DEBUG level for troubleshooting IAM authentication issues
- **NFR-005**: Cloud SQL connector MUST automatically refresh IAM tokens before expiration (default 1 hour) to prevent connection failures
- **NFR-006**: System MUST handle transient database errors with exponential backoff retry (max 3 retries, 1s/2s/4s delays)
- **NFR-007**: Container image size MUST NOT increase by more than 50MB due to new dependencies

### Technical Requirements

- **TR-001**: SQLAlchemy engine MUST be created using Cloud SQL Python Connector as connection factory (Connector.connect as creator callable)
- **TR-002**: Connection string format MUST be postgresql+psycopg:// (psycopg3 driver) not postgresql+psycopg2://
- **TR-003**: PGVector initialization MUST use collection_name parameter for data scoping (e.g., collection_name="hansard")
- **TR-004**: PGVector MUST be configured with use_jsonb=True for metadata storage to enable efficient filtering
- **TR-005**: Migration script MUST support --dry-run and --execute modes with validation before applying changes
- **TR-006**: Migration script MUST preserve chunk_id by passing explicit ids parameter to add_documents()
- **TR-007**: Migration script MUST validate record counts match between source and destination tables before marking migration complete
- **TR-008**: New vector store adapter MUST expose identical async method signatures to legacy implementation (add_chunks, similarity_search, delete_by_speech_id)
- **TR-009**: Backend selection logic MUST fail-fast at startup if VECTOR_BACKEND value doesn't match available implementations
- **TR-010**: All langchain-google-vertexai (embeddings) and langchain-google-genai (models) dependencies MUST remain at >=2.0.0 (already LangChain 1.0 compatible)

## Dependencies *(mandatory)*

### Add New Dependencies

```toml
[project.dependencies]
langchain = ">=1.0.0"
langchain-postgres = ">=0.0.12"
langchain-google-vertexai = ">=2.0.0"  # Already compatible, update version constraint
langchain-google-genai = ">=2.0.0"     # Already compatible, update version constraint
psycopg = {extras = ["binary"], version = ">=3.1.0"}
sqlalchemy = ">=2.0.0"
google-cloud-sql-connector = ">=1.11.0"
pgvector = ">=0.3.0"
```

### Remove Blocking Dependencies

```toml
# Remove from pyproject.toml:
# langchain-google-cloud-sql-pg  # Blocks at langchain-core<1.0.0
```

### Unchanged Dependencies

- `fastmcp>=2.14.0` - MCP server framework
- `google-cloud-secret-manager` - Secret access
- `uvicorn` - ASGI server
- All other existing dependencies remain

## Out of Scope *(mandatory)*

1. **Hybrid search (vector + full-text)**: Current implementation doesn't have hybrid search; not adding it in this upgrade. Can be added later as separate feature using PostgreSQL tsvector.

2. **Custom table schema support**: Migration moves to langchain-postgres standard schema (langchain_pg_collection, langchain_pg_embedding). Not supporting custom table names/columns - this simplifies maintenance and future upgrades.

3. **Automatic background migration**: Migration is one-time manual operation run by administrator. Not implementing automatic migration on service startup to avoid startup delays and risks.

4. **Multi-collection support**: Current implementation uses single collection ("hansard"). Not adding multi-collection routing in this upgrade - single collection is sufficient for current use case.

5. **Vector index optimization**: Using default pgvector IVFFlat index from langchain-postgres. Not tuning index parameters (lists, probes) in initial implementation - can optimize later based on performance data.

6. **Async psycopg (asyncpg)**: Using psycopg3 in sync mode with asyncio.to_thread wrappers. Not implementing native async with asyncpg driver - sync approach is simpler and langchain-postgres primarily supports psycopg3.

7. **Multi-region database replication**: Cloud SQL replication strategy is out of scope for this feature - upgrade maintains current single-region deployment model.

8. **Backward migration (new schema → old schema)**: Migration is one-way. Rollback is achieved via VECTOR_BACKEND flag, not data reverse-migration. Keeping old table as backup is recommended but not automated.

## Architecture Impact *(mandatory)*

### Current Architecture

```
VectorStoreService (async)
  → langchain-google-cloud-sql-pg PostgresVectorStore
    → PostgresEngine.from_instance()  # Built-in IAM auth
      → Cloud SQL PostgreSQL + pgvector
        → Custom table: hansard_speeches
```

### New Architecture (VECTOR_BACKEND=postgres)

```
VectorStoreService (async)
  → PostgresVectorStoreAdapter (async wrapper)
    → asyncio.to_thread()
      → langchain-postgres PGVector (sync)
        → SQLAlchemy Engine (pooled)
          → google-cloud-sql-connector  # IAM auth
            → Cloud SQL PostgreSQL + pgvector
              → Standard tables: langchain_pg_collection, langchain_pg_embedding
```

### Legacy Fallback (VECTOR_BACKEND=legacy)

```
VectorStoreService (async)
  → langchain-google-cloud-sql-pg PostgresVectorStore (existing)
    → PostgresEngine.from_instance()
      → Cloud SQL PostgreSQL + pgvector
        → Custom table: hansard_speeches (read-only after migration)
```

### Component Changes

**New Components**:
- `src/storage/cloud_sql_engine.py`: SQLAlchemy engine factory with Cloud SQL connector integration
- `src/storage/postgres_vector_store.py`: Async adapter wrapping langchain-postgres PGVector
- `scripts/migrate_to_langchain_postgres.py`: One-time migration script with dry-run and validation

**Modified Components**:
- `src/storage/vector_store.py`: Add backend selection logic based on VECTOR_BACKEND env var
- `src/config.py`: Add VECTOR_BACKEND and POSTGRES_COLLECTION_NAME config vars
- `pyproject.toml`: Update dependencies as specified above

**Unchanged Components**:
- `src/mcp_server.py`: MCP tool definitions unchanged (implementation swapped transparently)
- `src/tools/`: All tool modules unchanged (use VectorStoreService interface)
- `src/auth/`: Authentication layer unchanged
- `src/middleware/`: Logging/error handling unchanged

### Data Model Changes

**New Tables** (langchain-postgres standard schema):

```sql
-- Collection metadata
CREATE TABLE langchain_pg_collection (
    uuid UUID PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    cmetadata JSONB
);

-- Vector embeddings
CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding VECTOR(768),  -- text-embedding-005 dimension
    document TEXT,
    cmetadata JSONB,
    custom_id VARCHAR
);

-- Many-to-many collection membership
CREATE TABLE langchain_pg_embedding_collection (
    embedding_id UUID REFERENCES langchain_pg_embedding(uuid) ON DELETE CASCADE,
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    PRIMARY KEY (embedding_id, collection_id)
);

-- Index for vector similarity search
CREATE INDEX ON langchain_pg_embedding USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Migration Mapping**:

```
hansard_speeches.chunk_id        → langchain_pg_embedding.custom_id
hansard_speeches.chunk_text      → langchain_pg_embedding.document
hansard_speeches.embedding       → langchain_pg_embedding.embedding
hansard_speeches.metadata        → langchain_pg_embedding.cmetadata
[new]                            → langchain_pg_collection (name='hansard')
```

### Security Impact

**Positive Changes**:
- IAM authentication maintained via google-cloud-sql-connector (no regression)
- Automatic IAM token refresh improves reliability (no manual token management)
- SQLAlchemy connection pooling reduces authentication overhead

**Risks**:
- New dependency (google-cloud-sql-connector) introduces additional attack surface - mitigated by using official Google package with active maintenance
- psycopg3 is newer than psycopg2 - fewer years of production hardening - mitigated by extensive testing in staging

**No Change**:
- MCP tool access control (admin-only) unchanged
- TLS encryption to Cloud SQL unchanged
- Service account permissions unchanged

### Performance Impact

**Expected Improvements**:
- SQLAlchemy connection pooling should reduce connection setup overhead (reuse connections)
- langchain-postgres uses JSONB for metadata (better filtering performance than JSON text)
- Modern psycopg3 driver may have better query performance than psycopg2

**Potential Regressions**:
- asyncio.to_thread wrapper adds ~1-2ms overhead per operation (acceptable for I/O-bound vector search)
- Schema change may affect query plans - requires ANALYZE after migration

**Monitoring Plan**:
- Compare P50/P95/P99 latency for search_hansard tool before/after upgrade
- Monitor database connection counts (should decrease due to pooling)
- Track migration script runtime on production-size datasets

## Migration Strategy *(mandatory)*

### Phase 0: Development Setup (Day 1)

1. Create feature branch `016-langchain-postgres-upgrade`
2. Update `pyproject.toml` dependencies:
   - Add langchain>=1.0.0, langchain-postgres>=0.0.12, psycopg[binary]>=3.1.0
   - Add google-cloud-sql-connector>=1.11.0, sqlalchemy>=2.0.0, pgvector>=0.3.0
   - Update langchain-google-vertexai>=2.0.0, langchain-google-genai>=2.0.0
   - Comment out (don't remove yet) langchain-google-cloud-sql-pg
3. Run `uv sync` and verify no dependency conflicts
4. Create `src/config.py` additions: VECTOR_BACKEND, POSTGRES_COLLECTION_NAME
5. Test: Import new packages in Python REPL, verify no import errors

### Phase 1: Cloud SQL Engine Factory (Day 1-2)

1. Create `src/storage/cloud_sql_engine.py`:
   - Implement `create_cloud_sql_engine()` function
   - Use `google-cloud-sql-connector` Connector class
   - Configure psycopg3 driver (postgresql+psycopg://)
   - Implement IAM authentication via connector
   - Add connection pooling (pool_size=5, max_overflow=10)
   - Add comprehensive debug logging
2. Create unit test `tests/unit/storage/test_cloud_sql_engine.py`:
   - Mock Connector.connect()
   - Verify connection string format
   - Test IAM token refresh behavior
3. Test: Run unit tests, verify mocked connections work

### Phase 2: Vector Store Adapter (Day 2-3)

1. Create `src/storage/postgres_vector_store.py`:
   - Implement `PostgresVectorStoreAdapter` class
   - Wrap langchain-postgres PGVector in async methods
   - Use asyncio.to_thread() for sync operations
   - Implement: async add_chunks(), async similarity_search(), async delete_by_speech_id()
   - Match exact interface of legacy implementation
2. Create unit test `tests/unit/storage/test_postgres_vector_store.py`:
   - Mock PGVector operations
   - Test async wrappers work correctly
   - Verify metadata handling
3. Test: Run unit tests with mocked PGVector

### Phase 3: Backend Selection (Day 3)

1. Update `src/storage/vector_store.py`:
   - Read VECTOR_BACKEND environment variable
   - Implement backend factory pattern
   - Add startup validation (fail if backend unavailable)
   - Log which backend is selected
2. Update `src/config.py`:
   - Add VECTOR_BACKEND with default "legacy"
   - Add POSTGRES_COLLECTION_NAME with default "hansard"
3. Test: Set VECTOR_BACKEND=postgres, verify new code path is used

### Phase 4: Integration Testing (Day 4)

1. Create `tests/integration/storage/test_postgres_integration.py`:
   - Test against dev Cloud SQL instance
   - Verify IAM authentication works
   - Test add, search, delete operations
   - Test metadata filtering
   - Compare results with legacy backend
2. Run full integration test suite:
   - Deploy to local dev environment
   - Set VECTOR_BACKEND=postgres
   - Run all MCP tool tests
   - Verify no regressions
3. Test: E2E test with real Cloud SQL connection

### Phase 5: Migration Script (Day 5)

1. Create `scripts/migrate_to_langchain_postgres.py`:
   - Implement --dry-run mode (show plan, don't modify)
   - Implement --execute mode (perform migration)
   - Read from hansard_speeches (or current table)
   - Write to langchain_pg_embedding with collection_id
   - Preserve chunk_id as custom_id
   - Batch processing (100 records at a time)
   - Progress reporting
   - Error handling with rollback on failure
   - Post-migration validation (count verification, spot-check searches)
2. Test migration on dev database:
   - Populate dev DB with test data
   - Run with --dry-run, verify plan
   - Run with --execute, verify migration succeeds
   - Run same searches on old and new tables, compare results
3. Document migration procedure in `specs/016-langchain-postgres-upgrade/migration-procedure.md`

### Phase 6: Staging Deployment (Day 6)

1. Deploy to staging environment:
   - Keep VECTOR_BACKEND=legacy initially
   - Verify service starts successfully
   - Run smoke tests with legacy backend
2. Run migration on staging database:
   - Backup staging database
   - Run migration script
   - Validate migration results
3. Switch to new backend:
   - Set VECTOR_BACKEND=postgres
   - Restart service
   - Run full E2E test suite
   - Monitor logs for errors
4. Performance baseline:
   - Run load test with search_hansard tool
   - Record P50/P95/P99 latencies
   - Compare to legacy backend baseline

### Phase 7: Production Rollout (Day 7)

1. Pre-deployment:
   - Review staging test results
   - Get approval for production migration
   - Schedule maintenance window (for migration)
2. Production migration:
   - Create Cloud SQL snapshot backup
   - Run migration script with --dry-run
   - Review migration plan
   - Run migration with --execute
   - Validate migration results
3. Gradual rollout:
   - Deploy new code with VECTOR_BACKEND=legacy (no behavior change)
   - Monitor for 1 hour
   - Switch to VECTOR_BACKEND=postgres for 10% of instances
   - Monitor for errors, compare latencies
   - If no issues, switch remaining instances
4. Monitor closely:
   - Watch Cloud SQL connection counts
   - Track search latency metrics
   - Monitor error rates
   - Check IAM authentication logs

### Phase 8: Cleanup (Day 8+)

1. After 1 week of stable production operation:
   - Remove VECTOR_BACKEND feature flag
   - Remove legacy code path (langchain-google-cloud-sql-pg)
   - Remove langchain-google-cloud-sql-pg from dependencies
   - Archive old hansard_speeches table (don't drop immediately)
2. After 1 month:
   - Drop old table if no issues (after final backup)
   - Update documentation to remove legacy references

### Rollback Plan

**If issues detected in Phase 6 (Staging)**:
- Set VECTOR_BACKEND=legacy
- Restart service
- Investigate issues in development environment
- No production impact

**If issues detected in Phase 7 (Production)**:
- Immediately set VECTOR_BACKEND=legacy on all instances
- Restart services (< 1 minute downtime)
- System reverts to pre-upgrade behavior
- Old table still intact (no data loss)
- Investigate and fix issues
- Re-attempt migration after fixes

**Critical Rollback Scenario**:
- If migration script fails mid-execution, it stops and logs error
- Manual intervention required to assess state
- Options: retry migration, rollback to legacy backend, restore from snapshot

## Testing Strategy *(mandatory)*

### Unit Tests

**Test File**: `tests/unit/storage/test_cloud_sql_engine.py`
- Mock google-cloud-sql-connector Connector
- Verify create_cloud_sql_engine() creates engine with correct parameters
- Test connection string format is postgresql+psycopg://
- Verify IAM authentication parameters passed to connector
- Test connection pool configuration (size, overflow, timeouts)

**Test File**: `tests/unit/storage/test_postgres_vector_store.py`
- Mock langchain-postgres PGVector class
- Test PostgresVectorStoreAdapter wraps sync methods with asyncio.to_thread
- Verify add_chunks() passes correct parameters to PGVector.add_documents()
- Verify similarity_search() converts between async/sync correctly
- Test metadata filtering is passed through correctly
- Test error handling propagates from sync to async context

**Test File**: `tests/unit/storage/test_vector_store.py` (update existing)
- Test backend factory selects correct implementation based on VECTOR_BACKEND
- Test startup validation fails with clear error if backend unavailable
- Verify PostgresVectorStoreAdapter is instantiated when VECTOR_BACKEND=postgres
- Test configuration injection (collection name, connection params)

### Integration Tests

**Test File**: `tests/integration/storage/test_postgres_integration.py`
- Requires dev Cloud SQL instance
- Test full IAM authentication flow (no mocks)
- Test add_documents with explicit IDs and metadata
- Test similarity_search returns expected results
- Test metadata filtering ($eq, $in, $and operators)
- Test delete operations
- Compare search results between legacy and postgres backends for same data
- Test connection pooling (multiple sequential operations reuse connection)

**Test File**: `tests/integration/test_mcp_tools.py` (update existing)
- Run against dev environment with VECTOR_BACKEND=postgres
- Test search_hansard tool end-to-end
- Test ingest_markdown_file tool end-to-end
- Test bulk_ingest_directory tool end-to-end
- Verify results match legacy backend behavior

### Migration Testing

**Test File**: `tests/integration/test_migration.py`
- Requires dev Cloud SQL with test data
- Test migration --dry-run produces correct plan
- Test migration --execute preserves all data
- Verify record counts match before/after
- Spot-check 10 random records for data integrity
- Test migration is idempotent (running twice doesn't duplicate)
- Test migration handles errors gracefully (partial migration rollback)

### Performance Testing

**Load Test**: `tests/performance/test_search_latency.py`
- Run 1000 search queries against both backends
- Record P50, P95, P99 latencies
- Verify postgres backend within 10% of legacy baseline
- Test concurrent search requests (10 simultaneous clients)
- Verify no connection pool exhaustion

**Migration Performance**: `tests/performance/test_migration_speed.py`
- Time migration of 10,000 records
- Verify completes within 5 minutes
- Monitor memory usage during migration
- Test batch processing doesn't cause memory leaks

### Acceptance Criteria

- [ ] All unit tests pass with >90% code coverage for new modules
- [ ] All integration tests pass on dev environment
- [ ] Migration script successfully migrates dev database with 100% data integrity
- [ ] Search results from postgres backend match legacy backend (semantic equivalence)
- [ ] P95 search latency within 10% of legacy baseline
- [ ] Feature flag rollback works (VECTOR_BACKEND=legacy restores full functionality)
- [ ] IAM authentication works in Cloud Run (verified in staging)
- [ ] No password-based authentication anywhere in new code
- [ ] All existing MCP tools work identically with new backend
- [ ] Production migration completes successfully with validation

## Success Criteria *(mandatory)*

1. **Zero Functional Regressions**: All existing MCP tools (search_hansard, ingest_markdown_file, bulk_ingest_directory) work identically to pre-upgrade behavior in blind testing

2. **Data Integrity**: Migration script processes 100% of existing records with zero data loss, verified by record count matching and spot-check validation

3. **Performance Parity**: P95 search latency within 10% of pre-upgrade baseline (target: <500ms for typical queries)

4. **Production Stability**: Service runs in production with VECTOR_BACKEND=postgres for 7 days with:
   - Zero rollbacks required
   - Error rate <0.1%
   - No Cloud SQL IAM authentication failures
   - No connection pool exhaustion incidents

5. **Rollback Capability Verified**: Successfully test rollback procedure in staging by switching VECTOR_BACKEND=legacy and confirming immediate return to previous behavior

6. **Security Maintained**: IAM authentication confirmed working in production via Cloud SQL audit logs (no password-based auth detected)

7. **Migration Success**: Migration script completes on production database within maintenance window (<30 minutes for estimated 50K records) with post-migration validation passing

## Open Questions *(mandatory)*

1. **Q**: What is the current record count in production hansard_speeches table?
   **Impact**: Determines migration runtime and whether batch processing needs tuning
   **Owner**: System Administrator
   **Due**: Before Phase 5 (Migration Script)

2. **Q**: Should we maintain the old hansard_speeches table after migration, or drop it immediately?
   **Impact**: Affects storage costs and provides safety net for rollback
   **Options**: (A) Keep for 30 days then drop, (B) Drop after 7 days if stable, (C) Keep indefinitely as archive
   **Owner**: Product Owner + DBA
   **Due**: Before Phase 7 (Production)

3. **Q**: What is acceptable maintenance window duration for production migration?
   **Impact**: Determines whether migration must run online or can be offline
   **Options**: (A) Zero downtime (complex), (B) 30-minute window (simple), (C) 1-hour window (safest)
   **Owner**: Product Owner
   **Due**: Before Phase 7 (Production)

4. **Q**: Should migration script support incremental migration (migrate in chunks over multiple runs)?
   **Impact**: Affects migration script complexity and enables zero-downtime migration
   **Options**: (A) All-or-nothing single run, (B) Support resumable migration with checkpoints
   **Owner**: Tech Lead
   **Due**: Before Phase 5 (Migration Script implementation)

5. **Q**: What is target timeline for removing legacy code path (langchain-google-cloud-sql-pg)?
   **Impact**: Affects dependency maintenance burden and code complexity
   **Options**: (A) 1 week after stable, (B) 1 month after stable, (C) 3 months after stable
   **Owner**: Tech Lead + Product Owner
   **Due**: After Phase 7 (Production) success

6. **Q**: Should we implement connection pool monitoring/alerting before production rollout?
   **Impact**: Affects troubleshooting capability if connection issues arise
   **Options**: (A) Add custom Prometheus metrics, (B) Rely on Cloud SQL monitoring, (C) Both
   **Owner**: DevOps + Tech Lead
   **Due**: Before Phase 7 (Production)

7. **Q**: What is the plan for future langchain-postgres schema changes (e.g., when upgrading to langchain-postgres 1.0)?
   **Impact**: Determines whether we need schema version tracking now
   **Options**: (A) Handle when needed, (B) Add schema versioning proactively, (C) Pin langchain-postgres version long-term
   **Owner**: Tech Lead
   **Due**: Before Phase 8 (Cleanup)
