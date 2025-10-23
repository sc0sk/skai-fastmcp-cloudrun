# Feature Specification: Token Verification

**Feature Branch**: `010-token-verification`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "Token Verification: Protect FastMCP server by validating bearer tokens issued by external systems. Implement JWTVerifier class supporting JWKS endpoint integration, symmetric key verification (HMAC), and static public key verification. Add IntrospectionTokenVerifier for opaque token validation via OAuth 2.0 Token Introspection (RFC 7662). Include StaticTokenVerifier and RSAKeyPair utilities for development/testing. Support environment-based configuration (FASTMCP_SERVER_AUTH_* variables) for deployment flexibility. Token verification treats MCP server as OAuth resource server, validating token signatures, expiration, audience claims without handling user authentication flows."

## User Scenarios & Testing

### User Story 1 - Production JWT Token Validation (Priority: P1)

As a system integrator deploying FastMCP in a production environment, I need the server to validate JWT bearer tokens issued by our existing authentication infrastructure so that only authorized clients can access MCP tools and resources.

**Why this priority**: This is the core security requirement for production deployments. Without token validation, the server cannot securely integrate with existing enterprise authentication systems.

**Independent Test**: Can be fully tested by configuring JWT verification with a JWKS endpoint, making requests with valid and invalid tokens, and verifying that only valid tokens grant access. Delivers immediate security value for production deployments.

**Acceptance Scenarios**:

1. **Given** server is configured with JWKS endpoint URL, issuer, and audience, **When** a client presents a valid JWT bearer token with matching issuer and audience, **Then** the server validates the token signature and grants access to requested resources
2. **Given** server is configured for JWT verification, **When** a client presents a token with invalid signature, **Then** the server rejects the request with authentication error
3. **Given** server is configured for JWT verification, **When** a client presents an expired token, **Then** the server rejects the request with token expiration error
4. **Given** server is configured for JWT verification, **When** a client presents a token with wrong audience claim, **Then** the server rejects the request with invalid audience error
5. **Given** server is configured for JWT verification, **When** a client presents a token with wrong issuer claim, **Then** the server rejects the request with invalid issuer error

---

### User Story 2 - Internal Microservice Token Validation (Priority: P1)

As a platform engineer managing internal microservices, I need the FastMCP server to validate tokens using shared symmetric keys (HMAC) so that services within our trusted network can authenticate without complex key infrastructure.

**Why this priority**: Many organizations use symmetric key authentication for internal services. This is equally critical for those deployment scenarios and represents a different authentication pattern from asymmetric JWT verification.

**Independent Test**: Can be tested independently by configuring HMAC-based verification with a shared secret, having internal services present HMAC-signed tokens, and verifying access control. Delivers value for microservice architectures.

**Acceptance Scenarios**:

1. **Given** server is configured with shared secret and HMAC algorithm (HS256/HS384/HS512), **When** a service presents a token signed with the same secret, **Then** the server validates the signature and grants access
2. **Given** server is configured for HMAC verification, **When** a service presents a token signed with a different secret, **Then** the server rejects the request
3. **Given** server is configured for HMAC verification, **When** a service presents a token with valid signature but expired timestamp, **Then** the server rejects the request

---

### User Story 3 - Opaque Token Validation via Introspection (Priority: P2)

As a security engineer integrating with an OAuth provider that issues opaque tokens, I need the FastMCP server to validate tokens through OAuth 2.0 Token Introspection so that the authorization server maintains full control over token lifecycle and revocation.

**Why this priority**: Opaque tokens are common in enterprise OAuth deployments and provide stronger security guarantees (immediate revocation, server-side state). This is important for high-security environments but secondary to JWT validation which is more common.

**Independent Test**: Can be tested by configuring introspection endpoint URL and client credentials, presenting opaque tokens, and verifying that the server queries the introspection endpoint to validate token status. Delivers value for OAuth-based architectures.

**Acceptance Scenarios**:

1. **Given** server is configured with introspection endpoint URL and client credentials, **When** a client presents an active opaque token, **Then** the server queries the introspection endpoint and grants access based on active status
2. **Given** server is configured for token introspection, **When** a client presents a revoked token, **Then** the introspection endpoint returns inactive status and the server rejects the request
3. **Given** server is configured with required scopes, **When** a client presents a token lacking required scopes, **Then** the server rejects the request with insufficient permissions error
4. **Given** server is configured for token introspection, **When** the introspection endpoint is unreachable, **Then** the server handles the error gracefully and denies access

---

### User Story 4 - Development Environment Token Testing (Priority: P3)

As a developer working on MCP integration locally, I need simple token validation mechanisms for development so that I can test authentication flows without setting up complete identity infrastructure.

**Why this priority**: This enables rapid development and testing but is not required for production functionality. Developers can work around missing dev tools but productivity is improved with them.

**Independent Test**: Can be tested by configuring static tokens with predefined claims, using test key pair generation utilities, and verifying that development workflows succeed without external dependencies. Delivers value for development productivity.

**Acceptance Scenarios**:

1. **Given** server is configured with static token mapping (token string → claims), **When** a developer presents a predefined development token, **Then** the server recognizes the token and loads associated claims
2. **Given** developer generates an RSA key pair for testing, **When** they create a test token using the private key, **Then** the server validates the token using the public key
3. **Given** server is running in development mode with static tokens, **When** server transitions to production configuration, **Then** static token validation is disabled and production verification is enabled

---

### User Story 5 - Environment-Based Configuration (Priority: P2)

As a DevOps engineer managing deployments across multiple environments, I need to configure token verification through environment variables so that the same application code can run in development, staging, and production with appropriate authentication for each environment.

**Why this priority**: Environment-based configuration is essential for modern deployment practices and CI/CD pipelines. This is important for operational efficiency but can be achieved through programmatic configuration if needed.

**Independent Test**: Can be tested by setting environment variables for JWT verification settings, starting the server without explicit programmatic configuration, and verifying that authentication behavior matches environment settings. Delivers value for deployment flexibility.

**Acceptance Scenarios**:

1. **Given** environment variables are set for JWKS-based JWT verification, **When** the FastMCP server starts, **Then** it automatically enables JWT verification with specified configuration
2. **Given** environment variables are set for HMAC-based verification, **When** the server starts, **Then** it enables symmetric key verification with specified algorithm and secret
3. **Given** different environment variables are set in staging vs production, **When** the same application code runs in each environment, **Then** each environment uses its respective authentication configuration
4. **Given** no authentication environment variables are set, **When** the server starts, **Then** it runs without authentication requirements (development default)

---

### Edge Cases

- What happens when JWKS endpoint is temporarily unavailable during token validation?
- How does the system handle malformed JWT tokens that cannot be parsed?
- What happens when a token is valid but contains no subject or client identifier claims?
- How does the system handle token validation when required scopes are specified but token contains no scope claims?
- What happens when symmetric key length is insufficient for specified HMAC algorithm?
- How does the system handle introspection endpoint responses that don't conform to RFC 7662?
- What happens when environment variables contain invalid values (malformed URLs, invalid algorithms)?
- How does the system handle concurrent requests during JWKS key rotation?
- What happens when a token is valid but was issued in the future (clock skew)?
- How does the system handle requests with multiple Authorization headers or malformed bearer token format?

## Requirements

### Functional Requirements

- **FR-001**: System MUST validate JWT bearer tokens by verifying cryptographic signatures using public keys from JWKS endpoints
- **FR-002**: System MUST validate JWT bearer tokens using static public keys (RSA or ECDSA) when JWKS endpoints are not available
- **FR-003**: System MUST validate JWT bearer tokens using shared symmetric keys with HMAC algorithms (HS256, HS384, HS512)
- **FR-004**: System MUST validate JWT issuer claims against configured expected issuer
- **FR-005**: System MUST validate JWT audience claims against configured expected audience
- **FR-006**: System MUST validate JWT expiration timestamps and reject expired tokens
- **FR-007**: System MUST validate opaque tokens through OAuth 2.0 Token Introspection (RFC 7662) by querying configured introspection endpoints
- **FR-008**: System MUST authenticate to introspection endpoints using client credentials (client ID and secret)
- **FR-009**: System MUST validate token scopes against configured required scopes for both JWT and opaque tokens
- **FR-010**: System MUST accept predefined static tokens with associated claims for development and testing purposes
- **FR-011**: System MUST provide utilities to generate RSA key pairs and create signed test tokens for development
- **FR-012**: System MUST support configuration through environment variables for all token verification settings (JWKS URI, issuer, audience, algorithm, required scopes, introspection endpoint, client credentials)
- **FR-013**: System MUST extract client identity information from validated tokens (subject, client ID) for authorization decisions
- **FR-014**: System MUST handle token validation errors gracefully and return appropriate authentication error responses
- **FR-015**: System MUST treat the MCP server as an OAuth resource server that validates tokens without participating in user authentication flows
- **FR-016**: System MUST reject tokens with invalid bearer token format in Authorization headers
- **FR-017**: System MUST periodically fetch and cache public keys from JWKS endpoints
- **FR-018**: System MUST handle JWKS endpoint failures without crashing the server
- **FR-019**: System MUST validate that symmetric keys meet minimum length requirements for specified HMAC algorithms
- **FR-020**: System MUST handle clock skew when validating token expiration and not-before timestamps (configurable tolerance of 60 seconds by default)

### Key Entities

- **Token Verifier**: Abstract concept representing a component that validates bearer tokens and extracts claims for authorization. May use different validation strategies (JWT signature verification, introspection endpoint queries, static token lookup).

- **JWT Token**: Self-contained token format containing signed claims including issuer, audience, subject, expiration, and optional scope claims. Validated through cryptographic signature verification.

- **Opaque Token**: Random string token whose state is maintained by the authorization server. Validated through network calls to introspection endpoints.

- **Token Claims**: Set of assertions contained within or associated with a token, including identity (subject/client ID), expiration, issuer, audience, and scopes/permissions.

- **JWKS Endpoint**: URL serving JSON Web Key Sets containing public keys for JWT signature verification. Keys may rotate over time.

- **Introspection Endpoint**: OAuth 2.0 endpoint (RFC 7662) that accepts opaque tokens and returns active status, expiration, scopes, and other token metadata.

- **Client Credentials**: Identifier and secret used by the MCP server to authenticate to introspection endpoints when validating opaque tokens.

- **Required Scopes**: Set of permissions that a token must contain for the client to access protected resources or tools.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Server correctly validates 100% of valid JWT tokens issued by configured identity providers within 100ms average response time
- **SC-002**: Server correctly rejects 100% of invalid tokens (expired, wrong signature, wrong issuer/audience) with appropriate error messages
- **SC-003**: Token validation adds less than 50ms latency overhead to request processing for JWT tokens with cached JWKS keys
- **SC-004**: Token validation through introspection endpoints completes within 200ms for 95th percentile of requests
- **SC-005**: Server successfully handles JWKS key rotation without dropping valid requests during transition period
- **SC-006**: Developers can set up local development environment with test token validation in under 5 minutes using provided utilities
- **SC-007**: Server configuration can be changed between development, staging, and production environments using only environment variable changes (no code modifications)
- **SC-008**: Server continues serving requests with cached JWKS keys when JWKS endpoint is temporarily unavailable (graceful degradation)
- **SC-009**: Token validation errors provide sufficient information for client debugging without exposing sensitive security details
- **SC-010**: System supports at least 10,000 concurrent requests with token validation enabled without performance degradation beyond SC-003 latency threshold
