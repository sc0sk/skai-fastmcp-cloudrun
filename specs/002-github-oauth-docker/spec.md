# Feature Specification: GitHub OAuth Authentication and Docker Deployment

**Feature Branch**: `002-github-oauth-docker`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "Add GitHub OAuth authentication using FastMCP OAuth proxy pattern and containerize application for Cloud Run deployment"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure MCP Client Authentication (Priority: P1)

Users connecting MCP clients (Claude Desktop, custom clients) need to authenticate via GitHub OAuth before accessing Hansard search and retrieval tools. The authentication flow should handle dynamic client registration and redirect URIs seamlessly.

**Why this priority**: Authentication is the foundational security requirement. Without it, the API is publicly accessible, which contradicts the constitution's NON-NEGOTIABLE GitHub OAuth principle.

**Independent Test**: Can be fully tested by attempting to connect an MCP client (e.g., Claude Desktop) to the server and verifying that:
1. Unauthenticated requests are rejected
2. OAuth flow completes successfully
3. Authenticated requests succeed

**Acceptance Scenarios**:

1. **Given** an unauthenticated MCP client, **When** it attempts to list tools, **Then** the server responds with an authentication required error
2. **Given** a user initiates OAuth authorization, **When** they approve access on GitHub, **Then** they receive valid access tokens
3. **Given** an authenticated MCP client with valid tokens, **When** it calls the search tool, **Then** the request succeeds and returns results

---

### User Story 2 - Production Deployment via Docker Container (Priority: P2)

Operations team needs to deploy the Hansard RAG server to Google Cloud Run using a Docker container that packages all dependencies, configuration, and the FastMCP application.

**Why this priority**: Containerization is required for Cloud Run deployment and provides reproducible builds, but authentication (P1) must work first.

**Independent Test**: Can be fully tested by:
1. Building the Docker image locally
2. Running the container with production environment variables
3. Verifying the MCP server responds on the expected HTTP port
4. Confirming Cloud Run deployment succeeds

**Acceptance Scenarios**:

1. **Given** the Dockerfile exists, **When** `docker build` is run, **Then** a working container image is created
2. **Given** environment variables are configured, **When** the container starts, **Then** the FastMCP server listens on port 8000
3. **Given** the container image is pushed to Artifact Registry, **When** Cloud Run deployment is triggered, **Then** the service becomes accessible at the configured domain

---

### User Story 3 - Environment-Based Configuration (Priority: P3)

Developers and operators need to configure OAuth credentials, database connections, and service URLs through environment variables without modifying code, supporting both local development and production deployments.

**Why this priority**: Environment configuration is essential for production but depends on OAuth (P1) and Docker (P2) being functional first.

**Independent Test**: Can be fully tested by:
1. Running the server with different `.env` configurations
2. Verifying each configuration is correctly applied
3. Confirming no secrets are hardcoded in source code

**Acceptance Scenarios**:

1. **Given** GitHub OAuth credentials in environment variables, **When** the server starts, **Then** it uses those credentials for authentication
2. **Given** different `BASE_URL` values for dev vs production, **When** the OAuth callback is invoked, **Then** it redirects to the correct URL
3. **Given** Cloud SQL connection details in environment, **When** the server initializes, **Then** it connects to the correct database instance

---

### Edge Cases

- What happens when GitHub is unavailable during OAuth flow?
- How does the system handle expired access tokens during a tool call?
- What occurs if the Docker container starts without required environment variables?
- How are OAuth callback URIs validated for untrusted clients?
- What happens when Cloud Run restarts the container mid-request?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement FastMCP OAuth Proxy pattern to bridge GitHub OAuth (non-DCR provider) with MCP client dynamic registration
- **FR-002**: System MUST register an OAuth application with GitHub and obtain client ID and secret
- **FR-003**: System MUST configure OAuth redirect URI as `https://mcp.simonkennedymp.com.au/auth/callback` (matching Cloud Run domain)
- **FR-004**: System MUST validate GitHub-issued JWT tokens using GitHub's JWKS endpoint
- **FR-005**: System MUST require authentication for all MCP tool calls (search, fetch, dataset_stats)
- **FR-006**: System MUST support MCP client dynamic registration (return fixed upstream credentials)
- **FR-007**: System MUST handle OAuth authorization code exchange with PKCE forwarding
- **FR-008**: System MUST store OAuth client registrations persistently (survive server restarts)
- **FR-009**: System MUST create a Dockerfile that packages Python 3.11+, uv, FastMCP, and all dependencies
- **FR-010**: Container MUST expose port 8000 for HTTP transport
- **FR-011**: Container MUST read configuration from environment variables (no hardcoded secrets)
- **FR-012**: System MUST support the following environment variables:
  - `FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider`
  - `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID`
  - `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET`
  - `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL`
  - `JWT_SIGNING_KEY` (production: for signing MCP client tokens)
  - `TOKEN_ENCRYPTION_KEY` (production: for encrypting OAuth upstream tokens)
  - `GCP_PROJECT_ID`
  - `CLOUD_SQL_CONNECTION_NAME`
  - `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - `VERTEX_AI_LOCATION`
  - `REDIS_HOST`, `REDIS_PORT` (production: for persistent token storage)
- **FR-013**: System MUST use persistent storage for OAuth token management in production:
  - Development: In-memory storage (default, acceptable for testing)
  - Production: Redis or Firestore for distributed token persistence
  - JWT signing keys and token encryption keys stored in Google Secret Manager
  - Client registrations survive server restarts and enable horizontal scaling
- **FR-014**: System MUST include health check endpoint for Cloud Run probes
- **FR-015**: Container MUST run as non-root user for security
- **FR-016**: System MUST log authentication events (successful/failed logins)

### Key Entities

- **OAuth Client Registration**: Represents MCP client metadata (client_id, redirect_uris, scopes)
- **Access Token**: GitHub-issued JWT containing user identity and permissions
- **OAuth Callback Transaction**: Temporary state linking authorization code to client redirect URI
- **Docker Image**: Self-contained deployment artifact with all runtime dependencies
- **Environment Configuration**: Collection of environment variables required for server operation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Unauthenticated MCP clients receive authentication error within 500ms of connection attempt
- **SC-002**: Authenticated users can complete OAuth flow and receive access tokens within 30 seconds
- **SC-003**: Docker image builds successfully in under 5 minutes
- **SC-004**: Container starts and responds to health checks within 10 seconds
- **SC-005**: Cloud Run deployment completes successfully and serves traffic within 2 minutes of container push
- **SC-006**: 100% of GitHub OAuth transactions complete without exposing client secrets or tokens in logs
- **SC-007**: Server survives restart without losing registered OAuth clients (persistent storage)
- **SC-008**: Zero hardcoded secrets found in source code or Docker image

## Assumptions

- GitHub OAuth application has already been created with redirect URI `https://mcp.simonkennedymp.com.au/auth/callback`
- Cloud Run service `hansard-mcp-server` exists and is configured with the custom domain
- Let's Encrypt SSL certificate is already provisioned for `mcp.simonkennedymp.com.au`
- Cloud SQL instance is running and accessible from Cloud Run (Cloud SQL Proxy or VPC connector)
- Artifact Registry repository exists for storing Docker images
- GitHub users who will authenticate have appropriate permissions (public profile access)
- All 64 speeches have been successfully ingested into the database
- Constitution v2.6.0 mandates GitHub OAuth as NON-NEGOTIABLE for production

## Dependencies

- Feature 001-hansard-rag-implementation (database schema, vector store, MCP tools)
- GitHub OAuth application credentials
- Google Cloud Platform project with Cloud Run, Cloud SQL, and Artifact Registry enabled
- Custom domain DNS configuration pointing to Cloud Run service
- FastMCP 2.12.0+ with OAuth Proxy support
- Python 3.11+ runtime
- Docker build environment

## Out of Scope

- OAuth token refresh logic (handled by FastMCP automatically)
- Multi-provider authentication (only GitHub for MVP)
- Role-based access control (all authenticated users have same permissions)
- Rate limiting per user
- OAuth scope customization (using default GitHub scopes)
- Multi-stage Docker builds for size optimization
- Kubernetes deployment (Cloud Run only)
- Local development with OAuth (can use `DANGEROUSLY_OMIT_AUTH` for testing)
