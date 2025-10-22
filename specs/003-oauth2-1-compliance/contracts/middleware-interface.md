# Middleware Interface Contract

**Feature**: OAuth 2.1 Compliance
**Component**: OAuthResourceParameterMiddleware
**Date**: 2025-10-22

## Interface Definition

### Middleware Class

```python
class OAuthResourceParameterMiddleware(BaseHTTPMiddleware):
    """
    Strips RFC 8707 'resource' parameter from OAuth authorize requests.

    Purpose: Enable OAuth 2.1 client compatibility with FastMCP's OAuth 2.0 implementation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process incoming HTTP requests and strip resource parameter if present.

        Args:
            request: Starlette Request object
            call_next: Next middleware/handler in chain

        Returns:
            Response from downstream handler

        Behavior:
            - If path == "/authorize" AND "resource" in query_params:
                - Remove "resource" from query parameters
                - Update request._url with modified query string
            - Otherwise: pass request through unmodified
        """
```

## Input Contract

### Request Inspection

**Path Matching**:
- Middleware MUST only modify requests where `request.url.path == "/authorize"`
- All other paths MUST pass through unmodified

**Parameter Detection**:
- Check for `resource` parameter using: `"resource" in request.query_params`
- If parameter not present, skip modification

### Example Input (OAuth 2.1 with RFC 8707)

```http
GET /authorize?response_type=code&client_id=abc123&redirect_uri=https%3A%2F%2Fchatgpt.com%2Fcallback&state=xyz789&code_challenge=...&code_challenge_method=S256&resource=https%3A%2F%2Fmcp.example.com%2Fmcp HTTP/1.1
Host: mcp.example.com
```

## Output Contract

### Modified Request (resource parameter stripped)

```http
GET /authorize?response_type=code&client_id=abc123&redirect_uri=https%3A%2F%2Fchatgpt.com%2Fcallback&state=xyz789&code_challenge=...&code_challenge_method=S256 HTTP/1.1
Host: mcp.example.com
```

### Unmodified Request (OAuth 2.0 without resource)

```http
GET /authorize?response_type=code&client_id=abc123&redirect_uri=https%3A%2F%2Fchatgpt.com%2Fcallback&state=xyz789&code_challenge=...&code_challenge_method=S256 HTTP/1.1
Host: mcp.example.com
```

**Output**: Request passes through unchanged (no `resource` parameter to strip)

## Behavior Contracts

### Invariants

1. **Non-destructive**: All parameters except `resource` MUST be preserved exactly
2. **Order-independent**: Parameter order MAY change (query string is dictionary-based)
3. **URL encoding**: Parameter values MUST maintain correct URL encoding
4. **Idempotent**: Running middleware twice produces same result as once

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Multiple `resource` parameters | `dict(query_params)` automatically handles; last value wins, then removed |
| Empty `resource` value (`resource=`) | Parameter still removed (empty value treated same as any value) |
| `resource` in body (POST) | Middleware ignores (only processes query parameters) |
| Non-`/authorize` path with `resource` | Parameter preserved (middleware only targets `/authorize`) |
| Malformed URL encoding | Starlette handles parsing; middleware operates on parsed dict |

## Performance Contract

### Latency Guarantees

- Dictionary lookup (`"resource" in query_params`): ~1μs
- URL reconstruction (if resource present): ~5-10μs
- **Total overhead**: <10ms per request (p99)

### Resource Usage

- Memory: O(n) where n = number of query parameters (typically <10)
- CPU: Single-threaded, non-blocking async operation
- No I/O operations (pure request transformation)

## Error Handling

### Non-throwing Guarantee

Middleware MUST NOT raise exceptions for:
- Missing `resource` parameter
- Malformed query strings (handled by Starlette)
- Invalid URL encoding (handled by Starlette)

If unexpected error occurs:
- Log error with `print()` or logging module
- Pass request through unmodified (fail-open for OAuth flow)

### Logging Contract

**Success case** (optional):
```python
print(f"✅ OAuth resource parameter middleware enabled (RFC 8707 compatibility)")
```

**Parameter stripping** (recommended for debugging):
```python
if "resource" in request.query_params:
    print(f"Stripped RFC 8707 resource parameter: {request.query_params['resource']}")
```

## Integration Points

### Middleware Stack Order

**Requirement**: OAuthResourceParameterMiddleware MUST run BEFORE GitHubWhitelistMiddleware

**Rationale**: Resource parameter must be stripped before OAuth validation

**Example**:
```python
# Add OAuth resource parameter middleware first
app.add_middleware(OAuthResourceParameterMiddleware)

# Then add whitelist middleware
if os.getenv("FASTMCP_SERVER_AUTH"):
    app.add_middleware(GitHubWhitelistMiddleware)
```

### FastMCP Integration

**Interaction with GitHubProvider**:
- Middleware runs before OAuth provider processes request
- OAuth provider receives modified request with `resource` parameter removed
- OAuth provider validation succeeds (no unknown parameters)

## Testing Contract

### Unit Test Requirements

1. **Test: Strip resource parameter**
   - Input: `/authorize?resource=https://example.com&client_id=abc`
   - Expected: `resource` removed, `client_id` preserved

2. **Test: Preserve non-authorize paths**
   - Input: `/token?resource=https://example.com`
   - Expected: `resource` preserved

3. **Test: Handle missing resource parameter**
   - Input: `/authorize?client_id=abc`
   - Expected: Request unmodified

4. **Test: Preserve other parameters**
   - Input: `/authorize?resource=x&state=y&code_challenge=z`
   - Expected: Only `resource` removed, `state` and `code_challenge` preserved

### Integration Test Requirements

1. **Test: OAuth 2.1 flow succeeds**
   - Simulate ChatGPT OAuth request with `resource` parameter
   - Expected: Authorization completes without 400 error

2. **Test: OAuth 2.0 flow still works**
   - Simulate standard OAuth request without `resource` parameter
   - Expected: Authorization completes normally (backward compatibility)

3. **Test: Performance within bounds**
   - Measure middleware latency
   - Expected: <10ms overhead

## Versioning

**Version**: 1.0.0
**Stability**: Stable
**Compatibility**: FastMCP 2.12.5+, Python 3.11+, Starlette (FastMCP bundled version)
