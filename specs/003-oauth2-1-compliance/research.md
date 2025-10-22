# Research: OAuth 2.1 Compliance

**Feature**: OAuth 2.1 Compliance
**Date**: 2025-10-22
**Status**: Complete

## Executive Summary

OAuth 2.1 is a consolidation of OAuth 2.0 with security best practices (BCP). The primary blocker for ChatGPT authentication was the RFC 8707 `resource` parameter, which FastMCP's GitHubProvider doesn't support. The solution is a lightweight Starlette middleware that strips this optional parameter before it reaches the OAuth handler.

## Research Areas

### 1. OAuth 2.1 vs OAuth 2.0

**Decision**: Implement compatibility layer via middleware rather than upgrading FastMCP

**Rationale**:
- OAuth 2.1 is backward compatible with OAuth 2.0 + security extensions
- FastMCP 2.12.5 already implements OAuth 2.0 with PKCE (the main OAuth 2.1 requirement)
- The only breaking difference is the RFC 8707 `resource` parameter, which is optional
- Middleware approach is non-invasive and maintains backward compatibility

**Alternatives Considered**:
1. **Upgrade FastMCP to 2.14.0+**: Rejected - version doesn't exist yet (latest is 2.12.5)
2. **Fork FastMCP and patch GitHubProvider**: Rejected - maintenance burden, delays upgrades
3. **Wait for FastMCP upstream fix**: Rejected - blocking ChatGPT integration indefinitely
4. **Implement custom OAuth provider**: Rejected - reinventing wheel, high complexity

**Key Findings**:
- OAuth 2.1 mandatory requirements ([draft-ietf-oauth-v2-1-11](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-11)):
  - PKCE (Proof Key for Code Exchange) - **FastMCP already enforces this** ✅
  - Removed implicit grant - **FastMCP doesn't use it** ✅
  - Removed resource owner password credentials - **FastMCP doesn't use it** ✅
  - Strict redirect URI matching - **FastMCP already validates** ✅
- RFC 8707 resource parameter is **optional extension**, not core OAuth 2.1

### 2. RFC 8707 Resource Indicators

**Decision**: Strip `resource` parameter at middleware level

**Rationale**:
- RFC 8707 defines optional `resource` parameter for OAuth authorization requests
- ChatGPT includes this parameter to indicate target resource URL
- FastMCP's OAuth parsing rejects unknown parameters with 400 Bad Request
- Stripping the parameter is safe because:
  - It's purely informational (not used for authorization decisions)
  - FastMCP's JWT tokens already scope access to the server
  - Server URL is already known via `base_url` configuration

**Alternatives Considered**:
1. **Validate and use resource parameter**: Rejected - FastMCP doesn't support resource-scoped tokens
2. **Return error to client**: Rejected - breaks ChatGPT integration
3. **Ignore parameter parsing errors**: Rejected - hides legitimate validation issues

**RFC 8707 Specification**:
- Parameter: `resource` (query string in `/authorize` endpoint)
- Format: Absolute URI indicating target resource
- Semantics: Client requests token scoped to specific resource
- Optional: Servers may ignore if resource indicators not supported

### 3. Starlette Middleware Implementation

**Decision**: Use `BaseHTTPMiddleware` with URL manipulation

**Rationale**:
- Starlette is FastMCP's underlying ASGI framework
- `BaseHTTPMiddleware` provides clean request interception
- `request._url` is mutable, allowing parameter removal
- Middleware runs before OAuth handler, preventing 400 errors

**Implementation Pattern**:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import URL

class OAuthResourceParameterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/authorize" and "resource" in request.query_params:
            query_params = dict(request.query_params)
            query_params.pop("resource", None)
            new_url = request.url.replace(query=str(URL("").replace(query_params=query_params).query))
            request._url = new_url
        return await call_next(request)
```

**Alternatives Considered**:
1. **ASGI middleware (lower level)**: Rejected - more complex, same result
2. **FastMCP custom route**: Rejected - OAuth routes handled by GitHubProvider internally
3. **Monkey-patch GitHubProvider**: Rejected - fragile, breaks on FastMCP updates

### 4. Testing Strategy

**Decision**: Unit tests for middleware + integration tests for OAuth flows

**Rationale**:
- Unit tests verify parameter stripping logic in isolation
- Integration tests validate end-to-end OAuth 2.1 flows
- Backward compatibility tests ensure OAuth 2.0 clients still work

**Test Cases**:
1. **Unit**: Middleware strips `resource` parameter from `/authorize` requests
2. **Unit**: Middleware ignores non-`/authorize` paths
3. **Unit**: Middleware handles missing `resource` parameter gracefully
4. **Integration**: ChatGPT OAuth flow completes without 400 errors
5. **Integration**: Standard OAuth 2.0 flow still works (backward compatibility)
6. **Integration**: MCP Inspector connects successfully
7. **Performance**: Middleware adds <10ms latency

### 5. Deployment Considerations

**Decision**: Zero-downtime deployment via Cloud Run revision

**Rationale**:
- Middleware is added to existing server code
- No database migrations or secret changes required
- Cloud Run gradually shifts traffic to new revision
- Rollback is instant if issues detected

**Deployment Checklist**:
- ✅ No new environment variables required
- ✅ No database schema changes
- ✅ No secret rotation needed
- ✅ Backward compatible with OAuth 2.0 clients
- ✅ Can roll back by deploying previous revision

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Middleware breaks existing OAuth flows | High | Comprehensive backward compatibility tests |
| Performance regression from URL manipulation | Low | URL parsing is fast (~microseconds), add performance tests |
| FastMCP upgrade conflicts with middleware | Medium | Middleware is isolated, easy to remove if upstream fixes |
| Multiple `resource` parameters edge case | Low | `dict(query_params)` handles duplicates automatically |

## Success Metrics

- OAuth 2.1 clients (ChatGPT) authenticate successfully (0% 400 errors)
- OAuth 2.0 clients maintain 100% success rate (backward compatibility)
- Middleware adds <10ms latency to authorization requests
- Zero security regressions (PKCE still enforced, tokens still encrypted)

## References

- [OAuth 2.1 Draft Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-11)
- [RFC 8707: Resource Indicators for OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc8707)
- [FastMCP GitHub OAuth Documentation](https://gofastmcp.com/servers/auth/github)
- [Starlette Middleware Documentation](https://www.starlette.io/middleware/)
