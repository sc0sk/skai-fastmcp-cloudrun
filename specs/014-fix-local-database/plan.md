# Technical Plan: Fix Local Database Connection for Testing

**Feature**: 014-fix-local-database  
**Created**: 2025-10-25  
**Status**: Draft

## Overview

Fix environment variable mismatch that prevents local database connections via Cloud SQL proxy. The code expects `DATABASE_PASSWORD` but `.env` uses `CLOUDSQL_PASSWORD`, causing authentication failures in local development.

## Architecture & Stack

**Existing Stack** (no changes):
- Python 3.12
- Cloud SQL Python Connector (langchain-google-cloud-sql-pg)
- PostgreSQL via Cloud SQL
- Cloud SQL Auth Proxy (v1) - Note: v1 is deprecated; v2 migration recommended for future

**Authentication Methods**:
1. **Password Auth** (local development): Uses username + password via proxy
2. **IAM Auth** (production): Uses service account via Cloud SQL connector

## Technical Approach

### Phase 0: Environment Configuration Fix (P1)

**Problem**: Code expects database user `postgres`, but `.env` configured with `postgresql` (doesn't exist in Cloud SQL instance)

**Solution**: Update `CLOUDSQL_USER` to `postgres` in `.env` file

**Files to Change**:
- `.env` - Change `CLOUDSQL_USER` from `postgresql` to `postgres`
- `.env.example` - Update documentation with correct username and auth guidance
- `src/storage/vector_store.py` - Already uses correct `DATABASE_PASSWORD` variable
- `src/storage/metadata_store.py` - Already uses correct `DATABASE_PASSWORD` variable

**Note**: Investigation revealed `.env` already had correct `DATABASE_PASSWORD` variable; the issue was username mismatch, not variable naming.

**Validation**: Verify both stores connect successfully with corrected username

### Phase 1: Cloud SQL Proxy Setup Script (P1)

**Problem**: Developers don't know how to start proxy correctly

**Solution**: Create `scripts/start_cloud_sql_proxy.sh` helper script

**Script Requirements**:
- Check if proxy binary exists
- Check if proxy already running
- Start proxy on correct port (5432 for local, or configurable)
- Provide clear error messages
- Support graceful shutdown

**Arguments**:
```bash
./scripts/start_cloud_sql_proxy.sh [--port PORT] [--instance INSTANCE]
```

**Default behavior**:
- Port: 5432
- Instance: From `CLOUDSQL_INSTANCE` env var
- Project: From `GCP_PROJECT_ID` env var

### Phase 2: Documentation Updates (P2)

**Files to Update**:
- `README.md` - Add "Local Development Setup" section
- `DATABASE_SETUP.md` - Add proxy instructions
- `.env.example` - Add clear comments about auth methods

**Documentation Requirements**:
1. Explain difference between password auth (local) and IAM auth (production)
2. Step-by-step proxy setup for new developers
3. Troubleshooting guide for common errors
4. Examples of both auth configurations

### Phase 3: Automated Proxy Management (P3 - Optional)

**Problem**: Manual proxy management is inconvenient

**Solution**: pytest fixture to auto-start/stop proxy

**Implementation**:
- Add `tests/conftest.py` fixture
- Check if proxy running before tests
- Start if needed
- Clean shutdown after tests
- Skip if `SKIP_PROXY_MANAGEMENT=true`

**Benefits**:
- Tests work out-of-box for new developers
- No manual proxy management
- Automatic cleanup

## Data Model

No data model changes - this is configuration only.

## Security Considerations

1. **Password Storage**: Passwords must stay in `.env` (gitignored), never in `.env.example`
2. **Proxy Security**: Local proxy only binds to localhost (127.0.0.1)
3. **Production**: Continue using IAM auth (no passwords)
4. **Documentation**: Clear warnings about which auth method for which environment

## Testing Strategy

### Unit Tests
- No new unit tests needed (configuration change only)

### Integration Tests
- `test_tools_direct.py` - Must pass with proxy running
- `test_mcp_tools.py` - Must pass with proxy running

### Manual Tests
1. Start proxy using new script
2. Run `test_tools_direct.py` - should pass without auth errors
3. Verify search returns results
4. Verify fetch returns speech data
5. Stop proxy - tests should fail with clear error

## Rollout Plan

### Phase 0 (Critical - Blocks Testing)
1. Fix `.env` variable name
2. Test connection with proxy
3. Verify all database operations work

### Phase 1 (High Priority)
1. Create proxy startup script
2. Test on fresh machine
3. Add to onboarding docs

### Phase 2 (Medium Priority)
1. Update all documentation
2. Add troubleshooting guide
3. Review with team

### Phase 3 (Low Priority - Nice to Have)
1. Implement pytest fixture
2. Test auto-management
3. Document for advanced users

## Success Metrics

- ✅ Zero "password authentication failed" errors with correct config
- ✅ New developer can connect to database in <5 minutes
- ✅ All test files pass locally with proxy
- ✅ Documentation includes working examples for both auth methods

## Dependencies

**External**:
- Cloud SQL Auth Proxy binary (must be installed by user)
- Valid database credentials in `.env`

**Internal**:
- Existing `src/storage/vector_store.py` (no changes needed)
- Existing `src/storage/metadata_store.py` (no changes needed)

## Risk Assessment

**Low Risk**:
- Only touches configuration, not business logic
- Easy to rollback (just revert `.env` changes)
- Production unaffected (uses IAM auth)

**Mitigations**:
- Test thoroughly with proxy before committing
- Document both auth methods clearly
- Keep production config separate

## Alternative Approaches Considered

### Alternative 1: Rename code to use CLOUDSQL_PASSWORD
- **Rejected**: `DATABASE_PASSWORD` is more generic and clear
- Breaking change for anyone who already has correct config

### Alternative 2: Support both variable names
- **Rejected**: Adds complexity, masks real issue
- Better to standardize on one name

### Alternative 3: Always use IAM auth locally
- **Rejected**: Requires service account setup, more complex
- Password auth via proxy is simpler for local dev
