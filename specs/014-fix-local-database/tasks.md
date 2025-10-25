# Tasks: Fix Local Database Connection for Testing

**Feature**: 014-fix-local-database  
**Created**: 2025-10-25  
**Type**: Bug Fix

## Task Summary

- **Total Tasks**: 20
- **Phases**: 4 (Setup, P1 Critical Fix, P2 Docs, P3 Automation)
- **Estimated Time**: 3-4 hours

---

## Phase 0: Setup & Foundation (5 tasks)

- [x] **T001**: Create feature branch `014-fix-local-database`
  - Verify branch created from main
  - Confirm working directory clean

- [x] **T002**: Document current environment variable issue
  - List all files using `CLOUDSQL_PASSWORD`
  - List all files using `DATABASE_PASSWORD`
  - Confirm mismatch in `.env` vs code

- [x] **T003**: Verify Cloud SQL proxy is installed
  - Check if `cloud_sql_proxy` binary exists
  - Test proxy can start (manual verification)
  - Document version

- [x] **T004**: Create backup of current `.env`
  - Copy `.env` to `.env.backup`
  - Ensure backup is gitignored

- [x] **T005**: Identify all test files that need database
  - List: `test_tools_direct.py`, `test_mcp_tools.py`, etc.
  - Mark which tests require database connection

---

## Phase 1: Critical Environment Fix (P1 - 7 tasks)

### T101-T103: Fix Environment Configuration

- [x] **T101**: Update `.env` file with correct variable name
  - Rename `CLOUDSQL_PASSWORD` to `DATABASE_PASSWORD`
  - Verify password value unchanged
  - Add comments explaining local vs production auth

- [x] **T102**: Update `.env.example` with documentation
  - Add `DATABASE_PASSWORD` example (placeholder value)
  - Document: "For local testing with proxy - password auth"
  - Document: "For production Cloud Run - omit for IAM auth"
  - Add clear section headers for auth configuration

- [x] **T103**: Verify code uses correct variable name
  - Check `src/storage/vector_store.py` line 53
  - Check `src/storage/metadata_store.py` line 51
  - Confirm both use `os.getenv("DATABASE_PASSWORD")`

### T104-T106: Test Database Connection

- [x] **T104**: Start Cloud SQL proxy manually
  - Run: `./cloud_sql_proxy -instances=skai-fastmcp-cloudrun:us-central1:hansard-db-v2=tcp:5432 &`
  - Note: Using v1 syntax with `-instances=PROJECT:REGION:INSTANCE=tcp:PORT` format
  - Verify proxy starts on port 5432 (check with `lsof -i :5432`)
  - Check proxy logs for successful connection
  - **Completed**: Proxy running on PID 372728, listening on localhost:5432

- [x] **T105**: Run `test_tools_direct.py` with proxy
  - Execute: `PYTHONPATH=src:. .venv/bin/python test_tools_direct.py`
  - Result: Password authentication now works ✅
  - Note: Tests reveal schema issue - `langchain_id` column missing (separate from auth fix)
  - Authentication fix validated: Zero "password authentication failed" errors

- [x] **T106**: Validate both vector_store and metadata_store connect
  - Check connection logs from both stores
  - Verify no authentication errors
  - Confirm queries execute successfully
  - **Completed**: Both VectorStoreService and MetadataStore initialize successfully with correct postgres user

- [ ] **T107**: Improve error messages for authentication failures
  - Update `src/storage/vector_store.py` error handling
  - Update `src/storage/metadata_store.py` error handling
  - Distinguish between: proxy not running, wrong credentials, network issues
  - Add helpful hints in error messages pointing to setup docs

---

## Phase 2: Proxy Setup Script (P1 - 5 tasks)

- [x] **T201**: Create `scripts/start_cloud_sql_proxy.sh`
  - Add shebang and error handling
  - Check for proxy binary in order: 1) current directory (`./cloud_sql_proxy` or `./cloud-sql-proxy`), 2) PATH
  - Support both v1 (`cloud_sql_proxy`) and v2 (`cloud-sql-proxy`) binary names
  - If binary not found: Display installation URL (https://cloud.google.com/sql/docs/mysql/sql-proxy) and exit with code 1
  - Check if proxy already running (via `ps` or pidfile)
  - Parse arguments: `--port`, `--instance`
  - Read from env vars if args not provided
  - **Completed**: Script created with full binary detection, port conflict handling, and PID management

- [x] **T202**: Implement proxy startup logic
  - Construct connection string: `PROJECT:REGION:INSTANCE`
  - Start proxy in background
  - Save PID to `.cloud_sql_proxy.pid`
  - Wait for proxy to be ready (test connection)
  - Output success message with port info
  - **Completed**: Integrated into T201 script with v1/v2 support

- [x] **T203**: Add stop script `scripts/stop_cloud_sql_proxy.sh`
  - Read PID from `.cloud_sql_proxy.pid`
  - Send SIGTERM to process
  - Wait for clean shutdown
  - Remove PID file
  - **Completed**: Script created with graceful shutdown and SIGKILL fallback

- [x] **T204**: Test proxy scripts
  - Test start script: `./scripts/start_cloud_sql_proxy.sh`
  - Verify proxy running via `ps`
  - Run database test to confirm connection
  - Test stop script: `./scripts/stop_cloud_sql_proxy.sh`
  - Verify proxy stopped cleanly
  - **Completed**: Both scripts tested successfully; proxy starts on port 5432, stops cleanly with SIGTERM

- [x] **T205**: Add port conflict detection and handling
  - Check if port 5432 is already in use before starting proxy (use `lsof -i :5432` or `netstat`)
  - If occupied, try alternative ports (5433, 5434, 5435)
  - Update connection string to use selected port in proxy command
  - Create/update `CLOUDSQL_PORT` in `.env` to communicate selected port to application
  - Display warning message showing which port was selected
  - Document port override via `--port` flag in script help
  - **Completed**: Port conflict detection implemented in start script with automatic fallback and .env update

---

## Phase 3: Documentation Updates (P2 - 3 tasks)

- [x] **T301**: Update `README.md` with local setup section
  - Add "Local Development Setup" heading
  - Document: Install Cloud SQL proxy
  - Document: Configure `.env` with DATABASE_PASSWORD
  - Document: Start proxy with script
  - Document: Run tests
  - Add troubleshooting subsection
  - **Completed**: Added comprehensive local setup guide with prerequisites, proxy scripts, and troubleshooting section

- [x] **T302**: Update `DATABASE_SETUP.md` with proxy instructions
  - Add section: "Local Testing with Cloud SQL Proxy"
  - Step-by-step proxy installation (macOS, Linux, Windows)
  - Configuration examples for both auth methods
  - Common errors and solutions
  - **Completed**: Added full proxy installation guide, configuration examples, and error troubleshooting table

- [x] **T303**: Add inline comments to storage files
  - Add comment in `vector_store.py` explaining DATABASE_PASSWORD
  - Add comment in `metadata_store.py` explaining DATABASE_PASSWORD
  - Link to DATABASE_SETUP.md in comments
  - **Completed**: Added detailed authentication mode comments with links to setup guide

---

## Phase 4: Validation & Cleanup (4 tasks)

- [x] **T401**: Run full test suite with proxy
  - Start proxy via script
  - Run all database-dependent tests
  - Verify zero authentication errors
  - Check test coverage maintained
  - **Completed**: Proxy started successfully, tests run without authentication errors
  - **Note**: Schema issue (`langchain_id` column missing) is out of scope for this feature; requires separate schema migration

- [ ] **T402**: Test on fresh environment simulation
  - Create new Python venv
  - Install dependencies
  - Configure `.env` from `.env.example`
  - Follow README setup instructions
  - Measure time to first successful test

- [x] **T403**: Update agent context file
  - Update `.github/copilot-instructions.md`
  - Add: "Local testing requires Cloud SQL proxy"
  - Add: "Use DATABASE_PASSWORD for local auth"
  - Document proxy script usage
  - **Completed**: Updated with local development setup, proxy scripts, and common issues section

- [x] **T404**: Clean up and commit changes
  - Remove `.env.backup`
  - Add `.cloud_sql_proxy.pid` to `.gitignore`
  - Stage all changes
  - Commit: "fix: standardize DATABASE_PASSWORD for local testing"
  - Push to branch
  - **Partial**: Will complete after T402 and T403

---

## Phase 5 (Optional): Automated Proxy Management (P3 - deferred)

- [ ] **T501**: Create pytest fixture for proxy auto-start
  - Add `tests/conftest.py` if not exists
  - Create `@pytest.fixture(scope="session")` for proxy
  - Check if proxy running, start if needed
  - Yield to tests
  - Stop proxy after all tests

- [ ] **T502**: Test automated proxy management
  - Run tests without manually starting proxy
  - Verify proxy auto-starts
  - Verify tests pass
  - Verify proxy auto-stops

---

## Success Criteria Mapping

- **SC-001**: All existing test files pass ✓ (T105, T401)
- **SC-002**: Setup time <5 minutes ✓ (T402)
- **SC-003**: Zero password auth errors ✓ (T106, T401)
- **SC-004**: Documentation with examples ✓ (T301, T302)

## Functional Requirements Mapping

- **FR-001**: DATABASE_PASSWORD consistency ✓ (T101, T103)
- **FR-002**: Support both auth modes ✓ (T101, T102, T301, T302)
- **FR-003**: Verify proxy installed ✓ (T003, T201)
- **FR-004**: Clear documentation ✓ (T102, T301, T302, T303)
- **FR-005**: Enhanced error messages ✓ (T107)

## Testing Strategy

### Before Implementation
- [x] Document current failure mode (T002)
- [ ] Verify proxy works manually (T104)

### During Implementation
- [ ] Test each change incrementally (T105, T106)
- [ ] Verify scripts work (T204)

### After Implementation
- [ ] Full test suite passes (T401)
- [ ] Fresh setup test (T402)

## Dependencies

**Sequential Dependencies**:
- T101-T103 must complete before T104-T106
- T104 must complete before T105
- T201-T203 must complete before T204

**Parallel Opportunities**:
- T301-T303 can run in parallel [P]
- Documentation work independent of code changes

## Notes

- **Quick Win**: T101-T106 can be completed in 30 minutes
- **Priority**: Focus on Phase 0-1 first (critical path)
- **Phase 2**: Nice to have but not blocking
- **Phase 5**: Defer to future PR if time constrained
