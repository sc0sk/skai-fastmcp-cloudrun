# Feature Specification: MCP OAuth 2.1 Compliance and Security Hardening

**Feature Branch**: `011-mcp-oauth21-security`
**Created**: 2025-10-24
**Status**: Draft
**Input**: User description: "Update token verification feature to comply with MCP 2025 OAuth 2.1 specification and fix critical security vulnerabilities"

## User Scenarios & Testing

### User Story 1 - Secure JWT Token Validation with JWKS (Priority: P1)

As a **production MCP server operator**, I need the server to validate JWT access tokens from an external OAuth 2.1 authorization server using JWKS endpoints, so that only authenticated clients with valid bearer tokens can access MCP tools and resources.

**Why this priority**: This is the primary authentication mechanism for production deployments and is required for MCP 2025 specification compliance. Without this, the server cannot securely authenticate clients in enterprise environments.

**Independent Test**: Can be fully tested by configuring a JWKS endpoint URL, issuing a valid JWT token from an OAuth provider, and verifying that requests with valid tokens succeed while invalid/expired tokens are rejected with HTTP 401.

**Acceptance Scenarios**:

1. **Given** a valid JWT token from a trusted issuer with correct audience claim, **When** the client sends a request with `Authorization: Bearer <token>`, **Then** the server validates the signature using public keys from the JWKS endpoint and grants access
2. **Given** an expired JWT token, **When** the client sends a request, **Then** the server returns HTTP 401 with error "invalid_token"
3. **Given** a JWT token with wrong audience, **When** the client sends a request, **Then** the server returns HTTP 401 with generic error message (no config details leaked)
4. **Given** a JWT token with insufficient scopes, **When** the client attempts to access a protected resource, **Then** the server returns HTTP 403 with error "insufficient_scope"
5. **Given** JWKS endpoint keys are rotated, **When** a new token is issued with the new key, **Then** the server automatically fetches updated keys and validates the token successfully
6. **Given** multiple rapid authentication attempts with invalid tokens, **When** rate limit threshold is exceeded (10 attempts in 60 seconds), **Then** the server returns HTTP 429 and blocks further attempts for that token

---

### User Story 2 - Secure Secret Management (Priority: P1)

As a **security-conscious DevOps engineer**, I need the server to load sensitive configuration (JWKS URIs, OAuth client secrets, audience values) from Google Cloud Secret Manager in production and .env files in development, so that secrets are never committed to version control and support automatic rotation.

**Why this priority**: Credential exposure is a critical security risk. This enables secure secret management across all environments and is essential for production readiness.

**Independent Test**: Can be tested by storing secrets in Google Cloud Secret Manager, configuring the server to use `FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager`, and verifying that the server successfully retrieves and uses these secrets without them appearing in logs or environment variables.

**Acceptance Scenarios**:

1. **Given** secrets stored in Google Cloud Secret Manager, **When** the server starts in production, **Then** it retrieves secrets using the service account's IAM permissions and uses them for authentication configuration
2. **Given** a secret is rotated in Secret Manager (new version created), **When** the cached secret expires after TTL (300 seconds default), **Then** the server automatically fetches the new version on next access
3. **Given** the server is running in development mode with `.env` file, **When** the server starts, **Then** it loads secrets from the file (with warnings logged) and functions correctly
4. **Given** Secret Manager is temporarily unavailable, **When** the server attempts to retrieve a secret, **Then** it falls back to environment variables if available, or fails gracefully with clear error message
5. **Given** a secret contains sensitive data (client_secret, HMAC key), **When** the secret is loaded into a Pydantic model, **Then** it uses SecretStr type that prevents accidental logging in string representations

---

### User Story 3 - Algorithm Confusion Protection (Priority: P1)

As a **security architect**, I need the server to prevent algorithm confusion attacks where an attacker modifies a valid RS256 JWT to use HS256 with the public key as the HMAC secret, so that token verification cannot be bypassed through cryptographic attacks.

**Why this priority**: This is a critical vulnerability (CVE-level severity) that could allow complete authentication bypass. It must be fixed before production deployment.

**Independent Test**: Can be tested by creating a valid RS256 JWT, modifying its header to algorithm HS256, signing it with the public key used as HMAC secret, and verifying the server rejects it with HTTP 401.

**Acceptance Scenarios**:

1. **Given** JWT verification is configured with a JWKS endpoint, **When** the server initializes, **Then** it only allows asymmetric algorithms (RS256, RS384, RS512, ES256, ES384, ES512) and rejects configuration with HMAC algorithms
2. **Given** a JWT token with algorithm header "HS256", **When** the server is configured for RS256, **Then** the server rejects the token due to algorithm mismatch
3. **Given** HMAC verification is required, **When** the configuration specifies an HMAC algorithm (HS256/HS384/HS512), **Then** the server validates minimum key length (32/48/64 bytes) and rejects weak or test keys (repeated characters, common test strings)
4. **Given** a configuration mixing JWKS URI with HMAC algorithm, **When** the server validates the configuration, **Then** it raises a validation error preventing this insecure combination

---

### User Story 4 - OAuth 2.0 Token Introspection (Priority: P2)

As a **platform integrator**, I need the server to support OAuth 2.0 token introspection (RFC 7662) for validating opaque access tokens, so that I can use authorization servers that issue non-JWT bearer tokens.

**Why this priority**: Enables integration with enterprise OAuth servers that use opaque tokens instead of JWTs. Less critical than JWT support but required for certain enterprise deployments.

**Independent Test**: Can be tested by configuring an introspection endpoint URL and client credentials, issuing an opaque token, and verifying the server calls the introspection endpoint and correctly handles active/inactive responses.

**Acceptance Scenarios**:

1. **Given** an opaque access token and introspection endpoint configuration, **When** the client sends a request with the token, **Then** the server makes a POST request to the introspection endpoint with client credentials via Basic Auth
2. **Given** the introspection endpoint returns `{"active": true, "scope": "read:data"}`, **When** the server receives this response, **Then** it extracts the claims and grants access
3. **Given** the introspection endpoint returns `{"active": false}`, **When** the server receives this response, **Then** it returns HTTP 401 with error "invalid_token"
4. **Given** the introspection endpoint is slow to respond, **When** the request exceeds the timeout (10 seconds default), **Then** the server returns HTTP 500 with error "server_error" without exposing internal details
5. **Given** introspection client secret is configured, **When** the secret is loaded, **Then** it uses SecretStr type and never appears in logs or string representations

---

### User Story 5 - Development Testing Utilities (Priority: P3)

As a **developer testing MCP integrations locally**, I need the ability to use static token mappings and generate test RSA key pairs, so that I can develop and test authentication flows without requiring a full OAuth infrastructure.

**Why this priority**: Developer productivity feature. Useful for local development but not required for production. Lowest priority since it's a convenience feature with strict production guards.

**Independent Test**: Can be tested by configuring StaticTokenVerifier with predefined tokens, using RSAKeyPair to generate test keys and tokens, and verifying authentication works locally while production environment detection prevents misuse.

**Acceptance Scenarios**:

1. **Given** StaticTokenVerifier is configured with token mappings in development environment, **When** a request includes a configured static token, **Then** the server validates it against the mapping and grants access
2. **Given** ENVIRONMENT variable is set to "production" or Cloud Run environment is detected, **When** attempting to initialize StaticTokenVerifier, **Then** the system raises a validation error preventing usage
3. **Given** RSAKeyPair utility is used to generate keys in development, **When** attempting to export private key in production environment, **Then** the system raises an error refusing to export unencrypted private keys
4. **Given** DANGEROUSLY_OMIT_AUTH environment variable is set to true, **When** the server starts in production, **Then** it logs critical warnings and refuses to start (or starts in a degraded state with prominent warnings)

---

### User Story 6 - Rate Limiting and Brute Force Protection (Priority: P1)

As a **security operations engineer**, I need the server to rate-limit authentication attempts using a token bucket algorithm (10 attempts per 60 seconds per token hash), so that brute force attacks and denial-of-service attempts are mitigated.

**Why this priority**: Essential security control to prevent abuse. Without rate limiting, attackers can attempt unlimited authentication guesses or overwhelm the server with verification requests.

**Independent Test**: Can be tested by sending 11 consecutive requests with an invalid token within 60 seconds and verifying that the 11th request returns HTTP 429 with error "rate_limit_exceeded".

**Acceptance Scenarios**:

1. **Given** a client attempts authentication with invalid tokens, **When** 10 failed attempts occur within 60 seconds for the same token hash, **Then** the 11th attempt returns HTTP 429
2. **Given** rate limit is exceeded, **When** 60 seconds elapse, **Then** the rate limit window resets and new attempts are allowed
3. **Given** different tokens are used for authentication attempts, **When** each token is hashed separately, **Then** rate limits apply independently per token hash (preventing one malicious client from blocking legitimate users)
4. **Given** authentication attempts are occurring, **When** tokens are logged, **Then** only SHA-256 hashes appear in logs (not plaintext tokens)

---

### Edge Cases

- **What happens when JWKS endpoint is temporarily unreachable?**: Server should use cached JWKS keys if within TTL, or return HTTP 500 (server_error) if cache is stale, preventing authentication until endpoint is restored
- **How does system handle clock skew between client and server?**: System allows configurable clock skew tolerance (maximum 120 seconds, default 60 seconds) for timestamp validation (iat, exp, nbf claims)
- **What happens when multiple secrets with same name exist in Secret Manager?**: System uses "latest" version by default, or specific version if configured
- **How does system behave when OAuth provider changes JWKS keys without notice?**: JWKS client automatically fetches new keys when signature validation fails with cached keys, providing graceful key rotation handling
- **What happens when introspection endpoint returns malformed JSON?**: Server logs error details (sanitized) and returns HTTP 500 with generic "server_error" to client
- **How does system handle tokens with extremely large scope lists?**: System should implement maximum scope count validation (suggested limit: 100 scopes) to prevent resource exhaustion
- **What happens when rate limiting storage grows unbounded?**: Rate limiter implements automatic cleanup of expired entries (older than window duration)
- **How does system handle HTTPS certificate validation failures for JWKS/introspection endpoints?**: System rejects connection with HTTP 500 error, never allows insecure fallback to HTTP
- **What happens when Secret Manager returns old secret version during rotation?**: System compares version timestamp/number and logs warning if receiving older version than previously cached
- **How does system handle environment variable and Secret Manager both containing same secret?**: Secret Manager takes precedence over environment variables when backend is configured as "gcp_secret_manager"

## Requirements

### Functional Requirements

#### MCP 2025 OAuth 2.1 Compliance

- **FR-001**: System MUST act as OAuth 2.1 Resource Server only (not authorization server) and validate access tokens per OAuth 2.1 Section 5.2
- **FR-002**: System MUST verify JWT signatures using Identity Provider's JWKS URI with automatic key rotation support
- **FR-003**: System MUST validate JWT audience (aud) claim matches expected resource identifier before granting access
- **FR-004**: System MUST reject expired tokens (exp claim validation) with HTTP 401 response
- **FR-005**: System MUST extract bearer tokens only from Authorization header with "Bearer" scheme (never from query strings or other headers)
- **FR-006**: System MUST return HTTP 401 for invalid/expired/malformed tokens with error code "invalid_token"
- **FR-007**: System MUST return HTTP 403 for valid tokens with insufficient scopes with error code "insufficient_scope"
- **FR-008**: System MUST serve all endpoints over HTTPS in production (localhost HTTP allowed only for development)
- **FR-009**: System MUST validate issuer (iss) claim matches expected OAuth authorization server
- **FR-010**: System MUST implement token validation with configurable clock skew tolerance (maximum 120 seconds, default 60 seconds)

#### Security Hardening - Critical Fixes

- **FR-011**: System MUST prevent algorithm confusion attacks by enforcing algorithm whitelist: only asymmetric algorithms (RS256, RS384, RS512, ES256, ES384, ES512) allowed when using JWKS endpoints
- **FR-012**: System MUST validate HMAC key length meets minimum requirements: HS256 requires 32 bytes, HS384 requires 48 bytes, HS512 requires 64 bytes
- **FR-013**: System MUST reject weak HMAC keys including repeated characters, common test strings ("test", "secret", "password"), and low-entropy patterns
- **FR-014**: System MUST log only SHA-256 hashes of tokens (not plaintext tokens) in all log messages at all severity levels
- **FR-015**: System MUST enforce HTTPS for JWKS URIs in production (only http://localhost or http://127.0.0.1 allowed for development)
- **FR-016**: System MUST enforce HTTPS for introspection endpoints in production (only http://localhost or http://127.0.0.1 allowed for development)
- **FR-017**: System MUST implement rate limiting using token bucket algorithm: 10 authentication attempts per 60 seconds per token hash, returning HTTP 429 when exceeded
- **FR-018**: System MUST use Pydantic SecretStr type for all sensitive configuration values (client secrets, HMAC keys, introspection credentials)
- **FR-019**: System MUST return generic error messages to clients that do not leak configuration details (expected issuer, audience, algorithm)
- **FR-020**: System MUST log detailed errors server-side while returning generic messages to clients

#### Secret Management

- **FR-021**: System MUST support loading secrets from Google Cloud Secret Manager in production environments
- **FR-022**: System MUST support loading secrets from .env files in development environments with prominent warnings
- **FR-023**: System MUST support fallback from Google Cloud Secret Manager to environment variables when Secret Manager is unavailable
- **FR-024**: System MUST cache secrets retrieved from Secret Manager with configurable TTL (default 300 seconds)
- **FR-025**: System MUST automatically refresh cached secrets after TTL expiration on next access
- **FR-026**: System MUST support secret versioning with "latest" version as default or specific version number if configured
- **FR-027**: System MUST use IAM-based access control for Secret Manager using Cloud Run service account identity
- **FR-028**: System MUST fail securely when required secrets are unavailable (no insecure defaults)

#### Configuration

- **FR-029**: System MUST support environment variable `FASTMCP_SERVER_AUTH_TYPE` with values: jwt, introspection
- **FR-030**: System MUST support environment variable `FASTMCP_SERVER_AUTH_SECRET_BACKEND` with values: env, gcp_secret_manager
- **FR-031**: System MUST support configurable JWKS cache TTL (default 3600 seconds, range 60-86400 seconds)
- **FR-032**: System MUST support configurable rate limit parameters (attempts per window, window duration)
- **FR-033**: System MUST support configurable introspection timeout (default 10 seconds, maximum 60 seconds)
- **FR-034**: System MUST validate configuration at startup and refuse to start with invalid/insecure configuration

#### Development Utilities

- **FR-035**: System MUST provide StaticTokenVerifier for development with strict production environment detection
- **FR-036**: System MUST refuse to initialize StaticTokenVerifier when ENVIRONMENT=production or Cloud Run environment variables are detected
- **FR-037**: System MUST provide RSAKeyPair utility for generating test keys with production guards preventing unencrypted private key export
- **FR-038**: System MUST log prominent warnings when development utilities are used
- **FR-039**: System MUST support DANGEROUSLY_OMIT_AUTH flag for local testing with critical warnings and production detection

#### Performance and Reliability

- **FR-040**: Token validation latency MUST be under 100ms at 95th percentile under normal load
- **FR-041**: System MUST handle JWKS endpoint unavailability gracefully using cached keys when within TTL
- **FR-042**: System MUST implement automatic cleanup of expired rate limit entries to prevent memory growth
- **FR-043**: System MUST handle concurrent authentication requests safely with thread-safe rate limiting
- **FR-044**: System MUST validate HTTPS certificates for JWKS and introspection endpoints (no insecure certificate acceptance)

### Key Entities

- **Access Token**: Bearer credential (JWT or opaque) presented by client in Authorization header, containing claims about authenticated identity and granted permissions
- **Token Claims**: Validated identity and authorization information extracted from access token, including subject, client_id, scopes, issuer, audience, and expiration
- **JWKS (JSON Web Key Set)**: Collection of public cryptographic keys published by authorization server used to verify JWT signatures
- **Rate Limit Bucket**: Per-token-hash counter tracking authentication attempts within sliding time window for brute force prevention
- **Secret**: Sensitive configuration value (JWKS URI, OAuth client secret, HMAC key) stored in Secret Manager or environment variables
- **Verification Configuration**: Environment-specific settings defining how tokens are validated, including algorithm, issuer, audience, endpoints

## Success Criteria

### Measurable Outcomes

#### Security Compliance

- **SC-001**: All security audit critical vulnerabilities (algorithm confusion, weak HMAC keys, token logging, missing rate limiting) are fixed and verified through security tests
- **SC-002**: Server passes MCP 2025-03-26 specification compliance validation for OAuth 2.1 Resource Server requirements
- **SC-003**: Server passes OWASP API Security Top 10 validation for authentication and authorization controls
- **SC-004**: 100% of authentication operations log only token hashes (no plaintext tokens appear in any logs)
- **SC-005**: 100% of external endpoints (JWKS, introspection) enforce HTTPS in production (validated through configuration tests)

#### Functional Performance

- **SC-006**: Rate limiting successfully blocks brute force attacks: 11th authentication attempt within 60 seconds returns HTTP 429
- **SC-007**: Production environment guards prevent development utilities from being used: StaticTokenVerifier initialization fails in production with clear error message
- **SC-008**: All error messages returned to clients are generic and leak no configuration details (expected values, endpoints, algorithms)
- **SC-009**: Token validation latency is under 100ms at 95th percentile with 1000 concurrent requests
- **SC-010**: Secret rotation in Google Cloud Secret Manager is detected and applied within 300 seconds (TTL duration) without server restart

#### Integration Success

- **SC-011**: Server successfully validates JWT tokens from at least 2 major OAuth providers (Google, Microsoft, Auth0, Okta)
- **SC-012**: Server successfully retrieves and uses secrets from Google Cloud Secret Manager in Cloud Run environment
- **SC-013**: Server successfully falls back to environment variables when Secret Manager is unavailable (tested by disabling IAM permissions temporarily)
- **SC-014**: Developer can run server locally using .env file for configuration without requiring Google Cloud access

#### Reliability

- **SC-015**: JWKS key rotation handled gracefully: when authorization server rotates keys, new tokens are validated successfully within 5 seconds
- **SC-016**: System remains available during JWKS endpoint outage: cached keys continue working for requests until cache TTL expires
- **SC-017**: Rate limiter memory usage remains bounded: no memory leak observed after 1 million authentication attempts over 24 hours

## Assumptions

- OAuth authorization server (Identity Provider) is external and managed separately from MCP server
- Authorization server supports standard JWKS endpoints (RFC 7517) for JWT validation
- Authorization server issues access tokens with standard claims (iss, aud, exp, sub/client_id, scope)
- For HMAC validation, pre-shared keys are managed securely out-of-band between authorization server and resource server
- Google Cloud Secret Manager is available in production environments (Cloud Run deployment)
- Service account for Cloud Run has necessary IAM permissions for Secret Manager access (roles/secretmanager.secretAccessor)
- Introspection endpoints implement RFC 7662 standard response format
- Clock synchronization between servers is within reasonable bounds (NTP configured)
- Rate limiting is per-server instance (not distributed across multiple instances) - distributed rate limiting would require external state store
- Development environments have access to .env file support (python-dotenv or similar)
- Production environment is detectable via ENVIRONMENT variable or Cloud Run metadata
- HTTPS certificate validation uses system trust store (standard CA certificates)
- Token scopes follow space-separated string format or JSON array per OAuth 2.0 specification

## Out of Scope

- Implementation of OAuth 2.1 Authorization Server (only Resource Server functionality)
- PKCE flow implementation (handled by OAuth client, not resource server)
- User authentication UI (OAuth login pages)
- Token issuance and signing (handled by external authorization server)
- Distributed rate limiting across multiple server instances
- Token revocation list checking (server relies on short-lived tokens and expiration)
- DPoP (Demonstrating Proof-of-Possession) token binding (future enhancement)
- mTLS client certificate authentication
- Custom token claim validation rules (only standard claims: iss, aud, exp, nbf, scope)
- Token refresh logic (handled by OAuth clients)
- Multi-tenancy with per-tenant issuer configuration
- Audit logging to external SIEM systems (only standard application logging)
- Webhooks for custom authentication decisions
