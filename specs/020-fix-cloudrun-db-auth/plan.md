# Implementation Plan: Fix Cloud Run Database IAM Authentication

**Branch**: `019-fix-cloudrun-db-auth` | **Date**: 2025-11-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-fix-cloudrun-db-auth/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix Cloud Run IAM authentication for Cloud SQL PostgreSQL connections. The system currently falls back to `user="default"` in Cloud Run, causing authentication failures. The fix will properly detect the service account identity from Cloud Run's metadata service and use it as the database username. Local development with application default credentials must continue working. This is a TDD-driven fix with comprehensive tests for both environments.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `cloud-sql-python-connector>=1.10.0` (IAM auth with pg8000)
- `google-auth>=2.0.0` (credential detection)
- `sqlalchemy>=2.0.0` (connection management)
- `langchain-postgres>=0.0.12` (vector store)
- `pytest>=7.0`, `pytest-asyncio>=0.21` (TDD framework)

**Storage**: Cloud SQL PostgreSQL with pgvector extension
**Testing**: pytest with asyncio support, integration tests against real Cloud SQL
**Target Platform**: Cloud Run (Linux containers) + local development (Linux/macOS)
**Project Type**: Single project (backend service)
**Performance Goals**: Connection establishment <30s, maintain 10/10 test pass rate
**Constraints**: Must work in both Cloud Run (metadata service) and local (ADC file), no password auth, IAM-only
**Scale/Scope**: Single database, 3 connection pools (metadata, vector, ingestion), 62 speeches ingested

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Spec-First (NON-NEGOTIABLE)
✅ **PASS** - Feature has complete spec.md with user stories, functional requirements, success criteria

### II. Test-First Quality Gates
✅ **PASS** - TDD approach planned:
- Existing baseline: 10/10 tests passing locally (test_full_ingestion_tdd.py)
- New tests will be written first for Cloud Run IAM detection (failing)
- Implementation follows to make tests pass
- Regression: All existing tests must continue passing

### III. Async-Safe, Contract-Driven Design
✅ **PASS** - No contract changes:
- Internal fix to IAM user detection in CloudSQLEngine
- Public APIs (PostgresVectorStoreService, MCP tools) unchanged
- Async patterns already established (asyncio.to_thread for sync DB ops)

### IV. Security by Default
✅ **PASS** - Improves security:
- Enforces IAM authentication (no password fallback)
- Uses service account from metadata service (Cloud Run best practice)
- No credential embedding
- Logs IAM principal for audit trail

### V. Operational Simplicity
✅ **PASS** - Maintains simplicity:
- Uses standard Google Cloud libraries (google-auth, cloud-sql-python-connector)
- Configuration via environment variables (existing pattern)
- Clear error messages for misconfigurations
- No new dependencies required (all already in pyproject.toml)

**Constitution Check Result**: ✅ **ALL GATES PASS** - Ready for Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/019-fix-cloudrun-db-auth/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (IAM detection patterns)
├── data-model.md        # Phase 1 output (minimal - connection state)
├── quickstart.md        # Phase 1 output (testing guide)
├── contracts/           # Phase 1 output (N/A - internal fix)
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── storage/
│   ├── cloud_sql_engine.py         # FIX: IAM user detection logic
│   ├── postgres_vector_store.py    # EXISTING: Vector store service
│   ├── metadata_store.py            # EXISTING: Metadata store
│   └── embeddings.py                # EXISTING: Embedding service
├── tools/
│   ├── search.py                    # EXISTING: Search MCP tool
│   ├── fetch.py                     # EXISTING: Fetch MCP tool
│   └── ingest.py                    # EXISTING: Ingest MCP tool
├── config.py                        # EXISTING: Configuration
└── server.py                        # EXISTING: FastMCP server

tests/
├── test_full_ingestion_tdd.py       # EXISTING: 10 tests (baseline)
├── test_cloud_run_iam_auth.py       # NEW: Cloud Run IAM tests (TDD)
├── test_local_iam_auth.py           # NEW: Local ADC tests (TDD)
└── integration/
    └── test_cloud_sql_connection.py # NEW: Integration tests

# Debug/investigation files (temporary, not committed)
debug_iam_user.py                    # Debug script for IAM detection
test_cloud_run_search.py             # Cloud Run test script
GRANT_CLOUD_RUN_PERMISSIONS.sql      # SQL permission grants
```

**Structure Decision**: Single project structure (Option 1). This is an internal fix to the database connection layer (`src/storage/cloud_sql_engine.py`). No frontend, no API changes, no new modules. Tests follow the existing pattern in `tests/`.

## Complexity Tracking

> **No violations** - Constitution Check passed all gates. No complexity justification needed.

---

## Phase 0: Research & Investigation

### Research Questions

1. **IAM User Detection in Cloud Run**
   - How to detect service account from Cloud Run metadata service?
   - What's the API endpoint and format?
   - How does it differ from local ADC file parsing?

2. **Cloud SQL Connector IAM Auth**
   - How does cloud-sql-python-connector handle IAM auth with pg8000?
   - What's the correct way to pass service account email as database user?
   - Are there known issues with version <1.10.0?

3. **Error Patterns**
   - Why does `user="default"` appear in Cloud Run?
   - What causes "NoneType has no attribute 'decode'" error?
   - How to distinguish transient vs permanent auth failures?

4. **Testing Strategy**
   - How to mock Cloud Run metadata service for local tests?
   - How to test IAM auth without actual Cloud Run deployment?
   - How to preserve existing 10/10 test pass rate?

### Investigation Findings (from codebase analysis)

**Current State Analysis**:
- ✅ Local works: 10/10 tests pass with IAM auth (TDD_TEST_RESULTS_FULL_INGESTION.md)
- ❌ Cloud Run fails: Returns `user="default"` error
- ✅ Extension check: Already added in main (postgres_vector_store.py:317-340)
- ✅ No auto-create: `create_extension=False` already set (postgres_vector_store.py:361)

**Files Modified Recently** (git diff main):
- `src/storage/postgres_vector_store.py`: Added pgvector extension preflight check, disabled create_extension
- `pyproject.toml`: Upgraded cloud-sql-python-connector to >=1.10.0
- These changes are **committed to main** (commit 3ba327d)

**Debug Artifacts** (uncommitted):
- `GRANT_CLOUD_RUN_PERMISSIONS.sql`: Permission grants for Cloud Run SA
- `TDD_TEST_RESULTS_FULL_INGESTION.md`: Full test results (10/10 pass)
- `debug_iam_user.py`: IAM user detection debug script
- `test_cloud_run_search.py`: Cloud Run search test

**Next Phase**: Generate research.md with specific findings on IAM detection patterns.

---

## Phase 1: Design & Contracts

### Design Artifacts to Generate

1. **data-model.md**: Connection state model
   - IAMPrincipal: Detected identity (service account email)
   - ConnectionConfig: Cloud SQL parameters + IAM user
   - ConnectionState: Active, Failed, Retrying

2. **contracts/**: N/A (internal implementation, no API changes)

3. **quickstart.md**: Testing and validation guide
   - How to run TDD tests locally
   - How to test Cloud Run deployment
   - How to use debug endpoint
   - How to verify IAM user detection

### Agent Context Update

Will run `.specify/scripts/bash/update-agent-context.sh claude` after design phase to update CLAUDE.md with:
- TDD testing approach for IAM authentication
- Cloud Run metadata service patterns
- Local vs Cloud Run environment detection

---

## Phase 2: Task Generation

**Deferred to `/speckit.tasks` command** - Will generate dependency-ordered tasks including:

1. **Research Tasks**:
   - Investigate Cloud Run metadata service API
   - Document IAM user detection patterns
   - Identify Cloud SQL connector best practices

2. **TDD Tasks**:
   - Write failing test for Cloud Run IAM detection
   - Write failing test for local ADC detection
   - Write failing test for metadata service unavailability
   - Implement IAM user detection in CloudSQLEngine
   - Make all tests pass
   - Verify existing 10/10 tests still pass

3. **Validation Tasks**:
   - Deploy to Cloud Run
   - Test debug endpoint
   - Run full MCP tool suite
   - Monitor 24-hour stability

4. **Documentation Tasks**:
   - Update quickstart.md with testing procedures
   - Document IAM troubleshooting steps
   - Update CLAUDE.md with learnings

---

## Post-Design Constitution Re-Check

**Performed**: 2025-11-06 after Phase 1 design artifacts completed

### I. Spec-First (NON-NEGOTIABLE)
✅ **PASS** - All design artifacts generated:
- [x] plan.md - Complete with technical context, structure, phases
- [x] research.md - IAM detection patterns, best practices, error handling
- [x] data-model.md - IAMPrincipal, ConnectionConfig, ConnectionState models
- [x] quickstart.md - Comprehensive testing guide (TDD workflow)
- [x] contracts/README.md - No API changes documented
- [x] checklists/requirements.md - Spec quality validation (all passed)

### II. Test-First Quality Gates
✅ **PASS** - TDD workflow designed in quickstart.md:
- Phase 1: Run baseline tests (10/10 expected)
- Phase 2: Write failing tests for IAM detection
- Phase 3: Implement fix to make tests pass
- Phase 4: Run new tests (expect all pass)
- Phase 5: Regression test (10/10 still passing)
- Comprehensive test coverage: unit + integration + Cloud Run validation

### III. Async-Safe, Contract-Driven Design
✅ **PASS** - Contracts unchanged:
- data-model.md confirms internal state only (no public API changes)
- contracts/README.md documents 100% backward compatibility
- CloudSQLEngine properties are read-only additions (no breaking changes)
- Existing async patterns preserved (asyncio.to_thread for DB ops)

### IV. Security by Default
✅ **PASS** - Security improved:
- research.md documents IAM-only authentication (no password fallback)
- data-model.md includes validation to reject "default" placeholder
- Logging schema excludes passwords/tokens (non-sensitive data only)
- Follows principle of least privilege (service account from metadata)

### V. Operational Simplicity
✅ **PASS** - Maintains simplicity:
- No new dependencies (all in pyproject.toml already)
- quickstart.md provides clear testing procedures
- data-model.md includes troubleshooting logging schema
- Configuration remains environment variables (existing pattern)

**Result**: ✅ **ALL GATES PASS** - Design maintains constitution compliance

**Artifacts Generated**:
1. ✅ plan.md (this file)
2. ✅ research.md (IAM detection research)
3. ✅ data-model.md (internal state model)
4. ✅ quickstart.md (testing guide)
5. ✅ contracts/README.md (no API changes)
6. ✅ CLAUDE.md updated (agent context)

**Ready for**: `/speckit.tasks` - Task generation with TDD workflow
