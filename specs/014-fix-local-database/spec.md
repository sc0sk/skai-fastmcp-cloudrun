# Feature Specification: Fix Local Database Connection for Testing

**Feature Branch**: `014-fix-local-database`  
**Created**: 2025-10-25  
**Status**: Draft  
**Type**: Bug Fix  
**Input**: User description: "Fix local database connection for testing with Cloud SQL proxy"

## Problem Statement

The current implementation has a mismatch between environment variable names for database authentication:
- The code looks for `DATABASE_PASSWORD` 
- The `.env` file uses `CLOUDSQL_PASSWORD`
- This causes password authentication to fail in local development

Additionally, developers need clear guidance on:
1. How to start the Cloud SQL proxy for local testing
2. When to use password auth vs IAM auth
3. How to configure different auth methods

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local Development with Cloud SQL Proxy (Priority: P1)

**As a** developer working on the Hansard MCP server  
**I want to** connect to Cloud SQL database locally via proxy  
**So that** I can test MCP tools (search, fetch, ingest) against real data

**Why this priority**: This is critical for local development and testing. Without it, developers cannot verify their changes work with the actual database before deploying.

**Independent Test**: Can be fully tested by starting the proxy, running `test_tools_direct.py`, and verifying search/fetch operations return data without authentication errors.

**Acceptance Scenarios**:

1. **Given** Cloud SQL proxy is not running, **When** developer runs setup script, **Then** proxy starts and database connections succeed
2. **Given** `.env` is configured with correct password variable, **When** tools execute database queries, **Then** operations complete without "password authentication failed" errors
3. **Given** proxy is running on default port, **When** multiple tools access database concurrently, **Then** all connections succeed

---

### User Story 2 - Clear Documentation for Auth Configuration (Priority: P2)

**As a** new developer joining the project  
**I want** clear documentation on database authentication options  
**So that** I can quickly set up my local environment correctly

**Why this priority**: Reduces onboarding friction and prevents configuration errors that waste development time.

**Independent Test**: New developer can follow README instructions and successfully connect to database within 5 minutes.

**Acceptance Scenarios**:

1. **Given** fresh checkout of repo, **When** developer reads setup docs, **Then** they understand difference between password auth (local) and IAM auth (production)
2. **Given** developer wants to test locally, **When** they follow proxy setup guide, **Then** they can run all tests successfully
3. **Given** developer configures auth incorrectly, **When** they run tests, **Then** they see helpful error message pointing to documentation

---

### User Story 3 - Automated Proxy Management (Priority: P3)

**As a** developer  
**I want** the Cloud SQL proxy to start/stop automatically when needed  
**So that** I don't have to manually manage the proxy process

**Why this priority**: Nice-to-have quality-of-life improvement. Manual proxy management works fine, but automation would be more convenient.

**Independent Test**: Run test suite and verify proxy automatically starts if not running, and stops cleanly on exit.

**Acceptance Scenarios**:

1. **Given** proxy is not running, **When** developer runs test suite, **Then** proxy starts automatically before tests execute
2. **Given** tests complete, **When** test suite exits, **Then** proxy shuts down cleanly
3. **Given** proxy is already running, **When** tests start, **Then** existing proxy is reused without conflict

---

### Edge Cases

- What happens when Cloud SQL proxy binary is missing or outdated?
- How does system handle proxy connection failures (network issues, wrong credentials)?
- What if `.env` has both password AND IAM configuration set?
- How to handle port conflicts if 5432 is already in use?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use `DATABASE_PASSWORD` environment variable consistently across all database connection code
- **FR-002**: System MUST support both password authentication (local) and IAM authentication (production) modes
- **FR-003**: Setup script MUST verify Cloud SQL proxy is installed before attempting to start it
- **FR-004**: Configuration MUST clearly document which env vars are for local vs production
- **FR-005**: Error messages MUST indicate whether authentication failure is due to missing proxy, wrong credentials, or other causes

### Key Entities *(include if feature involves data)*

- **DatabaseConnection**: Encapsulates connection parameters (instance, database, user, password, auth method)
- **ProxyProcess**: Manages Cloud SQL proxy lifecycle (start, stop, health check)
- **AuthConfig**: Determines auth method based on environment variables

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing test files (`test_tools_direct.py`, `test_mcp_tools.py`) pass successfully when run locally with proxy
- **SC-002**: Setup time for new developers reduces from >30 minutes to <5 minutes
- **SC-003**: Zero "password authentication failed" errors when proxy is correctly configured
- **SC-004**: Documentation includes working examples for both local and production auth configurations
