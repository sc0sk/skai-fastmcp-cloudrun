# Feature Specification: FastMCP 2.13.0 Upgrade with Persistent OAuth Storage

**Feature Branch**: `001-fastmcp-oauth-persistence`
**Created**: 2025-11-06
**Status**: Draft
**Input**: User description: "Upgrade FastMCP to 2.13.0 and implement persistent OAuth client storage using PostgreSQL with encryption for GitHub OAuth Proxy dynamic client registration"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ChatGPT Maintains Authentication Across Deployments (Priority: P1)

When the MCP server is redeployed or restarted, ChatGPT users should not need to re-authenticate. Their OAuth client registration should persist automatically, allowing uninterrupted access to the server.

**Why this priority**: This is the critical user-facing issue causing immediate pain. ChatGPT users currently must manually re-authenticate after every server deployment, disrupting their workflow and reducing trust in the service.

**Independent Test**: Can be fully tested by: (1) Authenticating ChatGPT with the server, (2) Redeploying the server, (3) Attempting to use ChatGPT tools without re-authenticating. Success = tools work without "Client Not Registered" error.

**Acceptance Scenarios**:

1. **Given** ChatGPT has authenticated with the MCP server via GitHub OAuth, **When** the server is redeployed to Cloud Run, **Then** ChatGPT can continue using MCP tools without re-authentication
2. **Given** a valid OAuth client registration exists in the database, **When** the server starts up, **Then** it loads existing client registrations and accepts tokens from previously registered clients
3. **Given** ChatGPT has been inactive for 24 hours, **When** it attempts to use an MCP tool, **Then** the existing client registration is still valid and the request succeeds

---

### User Story 2 - Secure OAuth Client Storage (Priority: P2)

OAuth client credentials (client_id, client_secret) should be stored securely in the database with encryption at rest, following security best practices for sensitive credential storage.

**Why this priority**: Security is critical but the feature works without encryption (just less secure). This can be implemented after basic persistence is working.

**Independent Test**: Can be fully tested by: (1) Registering an OAuth client, (2) Inspecting the database directly, (3) Verifying client secrets are encrypted (not plaintext). Success = secrets are encrypted with Fernet encryption.

**Acceptance Scenarios**:

1. **Given** an OAuth client registers with the server, **When** the client credentials are stored in PostgreSQL, **Then** the client_secret is encrypted using Fernet encryption
2. **Given** encrypted client credentials in the database, **When** the server retrieves them for authentication, **Then** it successfully decrypts and validates the credentials
3. **Given** an attacker gains read access to the database, **When** they view the oauth_clients table, **Then** they cannot use the encrypted secrets without the encryption key

---

### User Story 3 - FastMCP 2.13.0 Framework Upgrade (Priority: P3)

The server should use FastMCP 2.13.0 with its official `client_storage` parameter support, replacing the current monkey-patching approach with the framework's built-in persistence mechanism.

**Why this priority**: This is a technical improvement that enables P1 and P2. It's not directly user-facing but provides the foundation for persistent OAuth storage.

**Independent Test**: Can be fully tested by: (1) Checking pyproject.toml shows FastMCP 2.13.0, (2) Verifying server starts without errors, (3) Confirming GitHubProvider accepts client_storage parameter. Success = no monkey-patching code remains.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** checking the installed FastMCP version, **Then** it shows version 2.13.0 or higher
2. **Given** GitHubProvider is configured with client_storage parameter, **When** the server starts, **Then** it uses the provided storage backend without errors
3. **Given** the upgrade is complete, **When** reviewing the codebase, **Then** all monkey-patching code (patch_github_provider_storage) has been removed

---

### Edge Cases

- What happens when the database is temporarily unavailable during OAuth client registration? System should fail gracefully with clear error message, not crash.
- How does system handle corrupted encrypted data in the oauth_clients table? System should log error and reject the client, requiring re-registration.
- What happens when encryption key changes between deployments? All existing OAuth clients become invalid (expected behavior - document this in deployment guide).
- How does system handle concurrent OAuth client registrations (race conditions)? PostgreSQL's ON CONFLICT handles this automatically.
- What happens when a client tries to register with duplicate redirect_uri? FastMCP's OAuth Proxy handles this per OAuth 2.0 spec.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST upgrade FastMCP dependency from 2.12.5 to 2.13.0 in pyproject.toml
- **FR-002**: System MUST use FastMCP 2.13.0's official `client_storage` parameter in GitHubProvider configuration
- **FR-003**: System MUST store OAuth client registrations in Cloud SQL PostgreSQL database
- **FR-004**: System MUST encrypt OAuth client secrets using Fernet symmetric encryption before storing
- **FR-005**: System MUST implement py-key-value-aio AsyncKeyValue interface for PostgreSQL storage backend
- **FR-006**: System MUST wrap storage backend with FernetEncryptionWrapper as recommended by FastMCP documentation
- **FR-007**: System MUST create oauth_clients table if it doesn't exist on server startup
- **FR-008**: System MUST store encryption key in Google Cloud Secret Manager (not in code or environment variables directly)
- **FR-009**: System MUST load existing OAuth client registrations from database on server restart
- **FR-010**: System MUST persist OAuth clients indefinitely (no automatic expiration)
- **FR-011**: System MUST support OAuth client deletion when clients explicitly unregister
- **FR-012**: System MUST handle database connection failures gracefully during OAuth operations
- **FR-013**: System MUST remove all monkey-patching code (patch_github_provider_storage) after upgrade
- **FR-014**: System MUST maintain compatibility with existing GitHub OAuth configuration (env vars, secrets)
- **FR-015**: System MUST use Cloud SQL IAM authentication for database connections from the OAuth storage backend

### Key Entities

- **OAuth Client Registration**: Represents a dynamically registered MCP client (like ChatGPT). Contains client_id (public identifier), client_secret (encrypted credential), redirect_uris (callback URLs), client_name (human-readable name), and registration timestamp. Persists indefinitely unless explicitly deleted.

- **Encryption Key**: Fernet symmetric encryption key used to encrypt/decrypt OAuth client secrets. Stored in Google Cloud Secret Manager as `OAUTH_STORAGE_ENCRYPTION_KEY`. Must be consistent across all server instances and deployments.

- **Storage Backend**: PostgreSQL-based implementation of py-key-value-aio's AsyncKeyValue interface. Provides async get/put/delete/exists/keys operations for OAuth client data. Wrapped with FernetEncryptionWrapper for automatic encryption.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ChatGPT users can use MCP tools continuously for 7 days without re-authentication, including across multiple server deployments
- **SC-002**: OAuth client registrations persist across 100% of server restarts and redeployments
- **SC-003**: Zero "Client Not Registered" errors occur for previously authenticated clients after deployment
- **SC-004**: OAuth client secrets stored in database are encrypted (verified by direct database inspection showing non-plaintext values)
- **SC-005**: Server startup time increases by no more than 2 seconds compared to current implementation
- **SC-006**: OAuth authentication flow completes in under 10 seconds from user initiation to successful tool access

## Assumptions *(mandatory)*

- FastMCP 2.13.0 officially supports the `client_storage` parameter (confirmed by FastMCP documentation)
- Cloud SQL PostgreSQL instance is already configured and accessible via IAM authentication
- Google Cloud Secret Manager is available for storing the encryption key
- Existing environment variables (FASTMCP_SERVER_AUTH_GITHUB_*) remain compatible with 2.13.0
- py-key-value-aio library is compatible with FastMCP 2.13.0's storage requirements
- Database schema can be modified (creating oauth_clients table) without affecting existing hansard_speeches data
- Server has necessary IAM permissions to access Secret Manager for encryption key
- OAuth clients registered before the upgrade will need to re-register once (acceptable one-time migration cost)

## Out of Scope *(mandatory)*

- **OAuth token refresh/rotation**: FastMCP's OAuth Proxy handles this automatically; not part of persistence implementation
- **Multi-region database replication**: Single-region Cloud SQL is sufficient; cross-region persistence is not required
- **OAuth client expiration/TTL**: Clients persist indefinitely; automatic cleanup is not implemented
- **Migration tool for existing OAuth clients**: Old clients will re-register; no migration path needed
- **Alternative storage backends**: Only PostgreSQL implementation; Redis/Memorystore alternatives not included
- **OAuth client management UI**: No admin interface for viewing/deleting clients; database access only
- **Audit logging of OAuth operations**: Basic application logs only; detailed audit trail not implemented
- **Rate limiting for client registration**: FastMCP's OAuth Proxy handles this; not part of persistence layer
- **Backup/restore procedures for OAuth clients**: Covered by existing Cloud SQL backup strategy

## Dependencies

- **FastMCP 2.13.0**: Framework upgrade required for official client_storage support
- **py-key-value-aio**: Async key-value interface library (dependency of FastMCP 2.13.0)
- **cryptography (Fernet)**: For encryption/decryption of client secrets
- **Cloud SQL PostgreSQL**: Existing database instance for persistent storage
- **Google Cloud Secret Manager**: For secure encryption key storage
- **google-cloud-sql-connector**: Already installed; used for database connections

## Risks

- **Risk**: FastMCP 2.13.0 has breaking API changes not documented
  - **Mitigation**: Test in development environment before deploying to production; check release notes thoroughly

- **Risk**: Encryption key loss or rotation causes all OAuth clients to become invalid
  - **Mitigation**: Document key management procedures; store backup of encryption key securely; plan for one-time re-authentication if key changes

- **Risk**: Database performance degrades with many OAuth client registrations
  - **Mitigation**: Add database indexes on frequently queried columns (client_id); monitor query performance; OAuth clients are small records (minimal impact expected)

- **Risk**: py-key-value-aio interface incompatibilities with PostgreSQL implementation
  - **Mitigation**: Write comprehensive unit tests for storage backend; verify all AsyncKeyValue methods work correctly; use FastMCP's recommended patterns

- **Risk**: Concurrent requests during deployment cause intermittent auth failures
  - **Mitigation**: Use Cloud Run's rolling deployment (gradual traffic shift); maintain old revision briefly during deployment; acceptable brief disruption during deploy window
