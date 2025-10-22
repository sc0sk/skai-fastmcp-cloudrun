# Data Model: OAuth 2.1 Compliance

**Feature**: OAuth 2.1 Compliance
**Date**: 2025-10-22

## Overview

This feature does not introduce new data entities or database schemas. It modifies HTTP request processing at the middleware level to handle OAuth 2.1-compliant authorization requests.

## Entities

### OAuth Authorization Request (HTTP Request - not persisted)

**Description**: HTTP GET request to `/authorize` endpoint containing OAuth parameters

**Attributes**:
- `client_id` (string, required): OAuth client identifier
- `redirect_uri` (string, required): URI to redirect after authorization
- `state` (string, required): CSRF protection token
- `code_challenge` (string, required): PKCE challenge for OAuth 2.1
- `code_challenge_method` (string, required): PKCE challenge method (S256)
- `response_type` (string, required): Fixed value "code"
- `resource` (string, optional, **RFC 8707**): Target resource URL (stripped by middleware)

**Relationships**: None - transient HTTP request

**Validation Rules**:
- All OAuth 2.0 parameters validated by FastMCP GitHubProvider
- `resource` parameter removed before validation if present
- PKCE parameters (`code_challenge`, `code_challenge_method`) must be present per OAuth 2.1

**State Transitions**: N/A - stateless HTTP request processing

### OAuth Middleware Configuration (Application State - not persisted)

**Description**: Middleware behavior configuration

**Attributes**:
- `enabled_paths` (list[string]): Paths where middleware applies (default: `["/authorize"]`)
- `stripped_parameters` (list[string]): Query parameters to remove (default: `["resource"]`)

**Note**: Configuration is hardcoded in middleware class; no runtime configuration needed for this feature.

## Data Flow

```
1. Client sends OAuth 2.1 request with `resource` parameter
   ↓
2. OAuthResourceParameterMiddleware intercepts request
   ↓
3. Middleware checks if path == "/authorize" AND "resource" in query_params
   ↓
4. If YES: Strip `resource` parameter from URL
   ↓
5. Modified request passed to GitHubProvider OAuth handler
   ↓
6. GitHubProvider validates OAuth 2.0 parameters (without `resource`)
   ↓
7. Authorization flow proceeds normally
```

## Storage Considerations

**No new storage required**:
- Existing OAuth token storage (Redis) unchanged
- Existing secret storage (Google Secret Manager) unchanged
- No database schema modifications
- No new configuration files

## Backward Compatibility

**OAuth 2.0 Clients** (without `resource` parameter):
- Middleware detects absence of `resource` parameter
- Request passes through unmodified
- 100% backward compatible

**OAuth 2.1 Clients** (with `resource` parameter):
- Middleware strips `resource` parameter
- Request becomes OAuth 2.0-compliant
- Authorization succeeds

## Performance Impact

**Request Processing**:
- Middleware adds one dictionary lookup: `"resource" in request.query_params` (~1μs)
- URL reconstruction only if `resource` present (~5-10μs)
- Expected overhead: <10ms per authorization request
- Authorization endpoint is low-frequency (once per client session)

## Security Considerations

**Parameter Stripping Safety**:
- `resource` parameter is informational only (RFC 8707)
- Does not affect authorization decisions
- FastMCP tokens are already server-scoped
- Removing parameter does not weaken security

**Audit Trail**:
- Middleware logs when `resource` parameter is stripped
- Cloud Run logs capture original request URL
- Enables debugging of OAuth 2.1 client behavior
