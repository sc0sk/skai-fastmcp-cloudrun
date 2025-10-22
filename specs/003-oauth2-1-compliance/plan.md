# Implementation Plan: OAuth 2.1 Compliance

**Branch**: `003-oauth2-1-compliance` | **Date**: 2025-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-oauth2-1-compliance/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable OAuth 2.1 compliance by adding middleware to handle RFC 8707 `resource` parameter in authorization requests. This allows modern OAuth 2.1 clients (like ChatGPT) to authenticate successfully while maintaining backward compatibility with standard OAuth 2.0 clients. The middleware strips the optional `resource` parameter before passing requests to FastMCP's GitHubProvider, which implements OAuth 2.0 with PKCE.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility)
**Primary Dependencies**: FastMCP 2.12.5+, Starlette (ASGI web framework), FastMCP GitHubProvider
**Storage**: Redis (production OAuth token storage), Google Secret Manager (JWT signing keys, token encryption keys)
**Testing**: pytest with async support
**Target Platform**: Cloud Run (Linux containers), HTTP transport
**Project Type**: Single project (FastMCP server)
**Performance Goals**: OAuth authorization requests complete in <5 seconds, middleware processing adds <10ms overhead
**Constraints**: Must maintain backward compatibility with OAuth 2.0 clients, no breaking changes to existing authentication
**Scale/Scope**: Small focused feature - single middleware class (~30 lines), impacts authorization endpoint only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. FastMCP Server-First Architecture
✅ **PASS** - No new MCP tools required. This feature enhances existing OAuth authentication infrastructure without adding tool surface area.

### II. Secure Authentication (NON-NEGOTIABLE)
✅ **PASS** - Strengthens OAuth 2.1 compliance using GitHubProvider OAuth Proxy pattern. Maintains all existing security requirements:
- PKCE enforcement (code_challenge/code_verifier validation)
- Persistent token storage (Redis + Google Secret Manager)
- JWT signing and token encryption with separate keys
- HTTPS-only production deployment
- No changes to authentication flow, only parameter handling

### III. Secrets Management (NON-NEGOTIABLE)
✅ **PASS** - No new secrets required. Uses existing environment variables and Cloud Run secrets:
- `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID`
- `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET`
- `JWT_SIGNING_KEY`
- `TOKEN_ENCRYPTION_KEY`

### IV. Test-Driven Development (NON-NEGOTIABLE)
✅ **PASS** - TDD required for middleware implementation:
1. Test: OAuth 2.1 requests with `resource` parameter succeed
2. Test: OAuth 2.0 requests without `resource` parameter still work (backward compatibility)
3. Test: Middleware strips `resource` parameter correctly
4. Test: Middleware adds minimal latency (<10ms)

### V. Structured Result Handling
✅ **N/A** - No MCP tools modified; middleware operates at HTTP request level

**Overall Status**: ✅ **ALL GATES PASSED** - Proceed to Phase 0 research

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── server.py           # MODIFIED: Add OAuthResourceParameterMiddleware
├── models/             # Unchanged
├── storage/            # Unchanged
├── tools/              # Unchanged
└── processing/         # Unchanged

tests/
├── unit/
│   └── test_oauth_middleware.py  # NEW: Middleware unit tests
└── integration/
    └── test_oauth_flows.py       # NEW: End-to-end OAuth 2.1 tests

deployment/
├── cloudbuild.yaml     # Unchanged (uses existing build process)
└── docker-compose.yml  # Unchanged
```

**Structure Decision**: Single project (FastMCP server). This feature modifies only `src/server.py` to add one new middleware class. All other code remains unchanged. Tests are added to existing test directories following the project's test structure.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

✅ **No violations** - All constitution gates passed. No complexity justifications required.

