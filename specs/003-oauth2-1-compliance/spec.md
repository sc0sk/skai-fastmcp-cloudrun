# Feature Specification: OAuth 2.1 Compliance

**Feature Branch**: `003-oauth2-1-compliance`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "OAuth 2.1"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ChatGPT OAuth Authentication (Priority: P1)

A user wants to connect their ChatGPT client to the MCP server using OAuth. The server must accept OAuth 2.1-compliant authorization requests from modern OAuth clients (like ChatGPT) that include optional RFC 8707 resource indicators.

**Why this priority**: This is critical for ChatGPT integration. Without OAuth 2.1 compliance, ChatGPT cannot authenticate with the server, making the entire service inaccessible to ChatGPT users. This represents the primary use case for the authentication system.

**Independent Test**: Can be fully tested by initiating an OAuth authorization flow from ChatGPT and verifying successful authentication without 400 Bad Request errors. Delivers immediate value by enabling ChatGPT access to the MCP server.

**Acceptance Scenarios**:

1. **Given** a ChatGPT user initiates OAuth authentication, **When** the authorization request includes a `resource` parameter (RFC 8707), **Then** the server accepts the request without returning 400 Bad Request
2. **Given** the server receives an authorization request with PKCE parameters, **When** the request includes optional RFC 8707 parameters, **Then** the server processes the authorization normally
3. **Given** a user completes OAuth authorization, **When** they attempt to use MCP tools, **Then** their authenticated session works correctly

---

### User Story 2 - Standard OAuth 2.0 Client Compatibility (Priority: P2)

A developer using a standard OAuth 2.0 client (without RFC 8707 extensions) wants to authenticate with the MCP server. The server must maintain backward compatibility with OAuth 2.0 clients while supporting OAuth 2.1 features.

**Why this priority**: Ensures the server doesn't break existing OAuth 2.0 integrations when adding OAuth 2.1 support. This maintains compatibility with the broader OAuth ecosystem.

**Independent Test**: Can be tested by connecting with an OAuth 2.0 client that doesn't send the `resource` parameter and verifying successful authentication.

**Acceptance Scenarios**:

1. **Given** an OAuth 2.0 client initiates authorization, **When** the request does not include a `resource` parameter, **Then** the server processes the request normally
2. **Given** a standard OAuth 2.0 authorization flow, **When** PKCE is used per OAuth 2.1 requirements, **Then** authentication completes successfully

---

### User Story 3 - MCP Inspector Testing (Priority: P3)

A developer wants to test the MCP server using the MCP Inspector tool with OAuth authentication enabled. The inspector must successfully connect to the server using OAuth 2.1-compliant flows.

**Why this priority**: Enables local development and testing of the OAuth implementation. While important for development, it's not critical for production use.

**Independent Test**: Can be tested by launching the MCP Inspector, connecting to the server URL, and completing the OAuth flow without errors.

**Acceptance Scenarios**:

1. **Given** a developer launches MCP Inspector, **When** they connect to the OAuth-protected server, **Then** the authorization flow completes without errors
2. **Given** the inspector sends OAuth requests, **When** the server processes them, **Then** the inspector successfully discovers and invokes MCP tools

---

### Edge Cases

- What happens when a client sends both OAuth 2.0 and OAuth 2.1 parameters simultaneously?
- How does the system handle malformed `resource` parameter values?
- What happens if a client sends multiple `resource` parameters in a single request?
- How does the server behave when the `resource` parameter doesn't match the expected server URL?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Server MUST accept OAuth authorization requests that include the optional `resource` parameter (RFC 8707)
- **FR-002**: Server MUST strip the `resource` parameter before passing requests to the OAuth provider implementation
- **FR-003**: Server MUST maintain backward compatibility with OAuth 2.0 clients that do not send the `resource` parameter
- **FR-004**: Server MUST enforce PKCE (Proof Key for Code Exchange) for all authorization requests per OAuth 2.1 requirements
- **FR-005**: Server MUST validate that `code_challenge` and `code_verifier` parameters are present in OAuth flows
- **FR-006**: Server MUST handle authorization requests from ChatGPT's OAuth client without returning 400 Bad Request errors
- **FR-007**: Server MUST log when the `resource` parameter is stripped for debugging and monitoring purposes
- **FR-008**: Server MUST process OAuth callbacks correctly regardless of whether the original request included a `resource` parameter

### Key Entities *(include if feature involves data)*

- **OAuth Authorization Request**: Contains standard OAuth 2.0 parameters (client_id, redirect_uri, state, code_challenge, code_challenge_method) plus optional RFC 8707 `resource` parameter indicating the target resource URL
- **OAuth Middleware**: Intercepts authorization requests and removes optional parameters not supported by the underlying OAuth provider before processing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ChatGPT users can successfully authenticate with the MCP server without encountering 400 Bad Request errors (100% success rate)
- **SC-002**: OAuth authorization requests complete in under 5 seconds from initiation to callback
- **SC-003**: Server maintains zero authentication failures for valid OAuth 2.0 clients after adding OAuth 2.1 support (backward compatibility)
- **SC-004**: Authorization request logs include clear indicators when RFC 8707 parameters are processed, enabling troubleshooting within 2 minutes
- **SC-005**: MCP Inspector successfully connects to the OAuth-protected server on first attempt without manual intervention
