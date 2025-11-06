# Feature Specification: Fix Cloud Run Database IAM Authentication

**Feature Branch**: `019-fix-cloudrun-db-auth`
**Created**: 2025-11-06
**Status**: Draft
**Input**: User description: "Fix Cloud Run database IAM authentication to resolve user='default' connection errors and enable production deployment"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Database Connection Works in Cloud Run Environment (Priority: P1)

When the Hansard MCP server is deployed to Cloud Run, it must successfully connect to Cloud SQL PostgreSQL using IAM authentication without falling back to default user credentials.

**Why this priority**: This is the critical blocker preventing production deployment. All MCP tools (search, fetch, ingest) depend on a working database connection. Without this, the service is non-functional in production.

**Independent Test**: Deploy to Cloud Run and call the `/debug/iam-user` endpoint. System should return the correct service account email (not "default") and successfully execute a test query against the database.

**Acceptance Scenarios**:

1. **Given** the server is deployed to Cloud Run with IAM-enabled service account, **When** the server starts and initializes database connections, **Then** the connection pool uses the Cloud Run service account identity (not "default")
2. **Given** a database connection is established in Cloud Run, **When** an MCP tool executes a query, **Then** the query succeeds without authentication errors
3. **Given** the debug endpoint is called from Cloud Run, **When** IAM user detection runs, **Then** it returns the full service account email (format: `SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com`)

---

### User Story 2 - Local Development Continues to Work (Priority: P2)

Developers working locally with service account credentials must continue to have working database connections using IAM authentication, maintaining the same test suite success rate.

**Why this priority**: This ensures we don't break the existing working local development workflow while fixing Cloud Run. The TDD test results show 10/10 tests passing locally, and this must be preserved.

**Independent Test**: Run `pytest tests/test_full_ingestion_tdd.py` locally with `USE_IAM_AUTH=true`. All 10 tests should pass with 100% ingestion coverage maintained.

**Acceptance Scenarios**:

1. **Given** a developer has service account credentials in `~/.config/gcloud/application_default_credentials.json`, **When** they run tests locally, **Then** all database operations succeed using IAM authentication
2. **Given** the local environment is configured with Cloud SQL parameters, **When** the vector store initializes, **Then** it connects using the service account email extracted from default credentials
3. **Given** tests run locally, **When** ingestion, search, and fetch operations execute, **Then** they complete successfully with the same performance metrics as documented in TDD results

---

### User Story 3 - Clear Error Messages for Misconfiguration (Priority: P3)

When database connection fails due to misconfiguration (missing IAM roles, wrong database name, network issues), the system provides clear diagnostic information to help operators identify and fix the issue.

**Why this priority**: Operational excellence - while not blocking deployment, good error messages reduce debugging time and improve maintainability. This is lower priority than getting connections working in the first place.

**Independent Test**: Intentionally misconfigure database parameters (e.g., wrong instance name, remove IAM role) and verify error messages clearly indicate the problem and suggest remediation steps.

**Acceptance Scenarios**:

1. **Given** the service account lacks `roles/cloudsql.client` permission, **When** connection initialization fails, **Then** the error message explicitly mentions the missing IAM role and suggests how to grant it
2. **Given** the pgvector extension is not enabled, **When** vector store initialization runs, **Then** the error message shows the exact SQL command needed to enable the extension
3. **Given** the database user doesn't match the IAM principal, **When** authentication fails, **Then** the error message displays both the expected user (service account email) and the attempted user for comparison

---

### Edge Cases

- What happens when Cloud Run's metadata service is temporarily unavailable during startup?
- How does the system handle IAM token refresh when a connection stays open for extended periods?
- What occurs if the service account's IAM database user is deleted after the service starts?
- How does the connection pool behave during Cloud SQL maintenance windows?
- What happens when the Cloud SQL instance is in a different region than the Cloud Run service?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect the correct IAM principal (service account email) when running in Cloud Run environment
- **FR-002**: System MUST use the detected service account email as the database username when establishing Cloud SQL connections
- **FR-003**: System MUST successfully authenticate to Cloud SQL PostgreSQL using IAM authentication (no password) in Cloud Run
- **FR-004**: System MUST validate pgvector extension availability before attempting to create vector store instances
- **FR-005**: System MUST provide a debug endpoint that reports the detected IAM user and connection status for troubleshooting
- **FR-006**: System MUST maintain backward compatibility with local development environment using application default credentials
- **FR-007**: System MUST retry transient connection failures (network timeouts, token refresh) with exponential backoff (existing: 1s, 2s, 4s)
- **FR-008**: System MUST fail fast with clear error messages for permanent configuration issues (missing IAM roles, wrong database name, extension not enabled)
- **FR-009**: Connection initialization MUST complete within the Cloud Run instance startup timeout (default: 10 minutes, practical target: <30 seconds)
- **FR-010**: System MUST log IAM authentication details at INFO level during startup to aid deployment verification

### Key Entities

- **Cloud SQL Connection**: Represents the database connection established using Cloud SQL Python Connector with IAM authentication. Key attributes: project ID, region, instance name, database name, IAM user (service account email), connection pool settings.
- **IAM Principal**: The identity used for database authentication. In Cloud Run: service account from metadata service. In local dev: service account from application default credentials. Must match a PostgreSQL IAM database user.
- **Vector Store Service**: Service that requires authenticated database connection to perform semantic search operations. Depends on successful IAM authentication and pgvector extension availability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: MCP server deployed to Cloud Run successfully connects to Cloud SQL on startup within 30 seconds
- **SC-002**: All 3 MCP tools (search, fetch, ingest) function correctly when called from Cloud Run, returning results within their existing performance targets (search: <10s, fetch: <1s, ingest: <60s per speech)
- **SC-003**: Local development tests continue to pass at 100% rate (10/10 tests in test_full_ingestion_tdd.py)
- **SC-004**: Debug endpoint returns correct service account email in Cloud Run environment (not "default")
- **SC-005**: Zero authentication errors appear in Cloud Run logs for successful database operations
- **SC-006**: Connection pool maintains stable connections over 24-hour period without IAM token expiry failures
- **SC-007**: Error messages for misconfiguration issues reduce troubleshooting time by 75% (measured by time from error to fix in test scenarios)

## Assumptions

- The Cloud Run service account has already been granted the required IAM roles (`roles/cloudsql.client`, `roles/cloudsql.instanceUser`)
- A PostgreSQL IAM database user matching the service account email has been created in the database
- The pgvector extension has been enabled by a privileged database user
- Cloud Run instances have network connectivity to the Cloud SQL instance (VPC connector or public IP configured)
- The Cloud SQL Python Connector library (v1.10.0+) correctly implements IAM authentication for the pg8000 driver
- Cloud Run's metadata service is available at startup for service account identity detection

## Dependencies

- Existing Cloud SQL instance with pgvector extension enabled
- Existing database schema (langchain_pg_collection, langchain_pg_embedding tables)
- Cloud SQL Python Connector library with pg8000 driver
- Cloud Run deployment with service account configured
- IAM permissions already granted to service account
- Existing test suite (test_full_ingestion_tdd.py) for regression validation

## Out of Scope

- Database schema migrations or changes to table structure
- Performance optimization of vector search operations (already meeting targets)
- Adding new MCP tools or features beyond fixing existing connection issues
- Changing embedding models or dimensions
- Implementing connection pooling strategies beyond existing configuration
- Adding support for password-based authentication (IAM-only)
- Multi-region database replication or failover
- Database backup and recovery procedures
