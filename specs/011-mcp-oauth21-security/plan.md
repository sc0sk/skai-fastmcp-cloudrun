# Implementation Plan: MCP OAuth 2.1 Compliance and Security Hardening

**Branch**: `011-mcp-oauth21-security` | **Date**: 2025-10-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-mcp-oauth21-security/spec.md`

## Summary

This feature updates the existing token verification system to comply with MCP 2025-03-26 OAuth 2.1 Resource Server specification while fixing critical security vulnerabilities identified in security audit. The implementation enhances JWT/introspection authentication with algorithm confusion protection, rate limiting, secure secret management via Google Cloud Secret Manager, and comprehensive security hardening measures.

**Primary Technical Approach**: Refactor existing `src/auth/` module to add algorithm whitelisting, implement token bucket rate limiter with SHA-256 token hashing, integrate Google Cloud Secret Manager with TTL-based caching, enforce HTTPS validation for external endpoints, and use Pydantic SecretStr for credential protection.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility)

**Primary Dependencies**:
- **Existing**: PyJWT[crypto]>=2.8.0, cryptography>=41.0.0, httpx>=0.25.0, Pydantic v2
- **New**: google-cloud-secret-manager>=2.16.0, python-dotenv>=1.0.0

**Storage**:
- In-memory rate limiting state (per-server instance, non-distributed)
- Google Cloud Secret Manager for production secrets
- .env files for development configuration

**Testing**:
- pytest with pytest-asyncio for async token verification tests
- pytest-httpx for mocking introspection endpoints
- Security-specific tests for algorithm confusion, rate limiting, token logging

**Target Platform**:
- Cloud Run (production) with service account IAM for Secret Manager
- Linux development environments with localhost HTTP support

**Project Type**: Single project (FastMCP server enhancement)

**Performance Goals**:
- Token validation latency <100ms p95
- Rate limiting decision <5ms overhead
- Secret cache retrieval <10ms (in-memory)
- JWKS key fetch <500ms (external call)

**Constraints**:
- MCP 2025-03-26 OAuth 2.1 Resource Server compliance (MUST requirements)
- Zero plaintext tokens in logs (security requirement)
- No distributed state (rate limiting per-instance only)
- Backward compatibility with existing FastMCP AuthProvider interface
- No breaking changes to existing MCP tool functionality

**Scale/Scope**:
- 44 functional requirements across 6 categories
- 6 user stories (4 P1, 1 P2, 1 P3 priority)
- 17 success criteria
- Security fixes for 2 critical, 4 high, 4 medium severity issues
- Integration with Google Cloud Secret Manager for secret management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| **II. Secure Authentication (NON-NEGOTIABLE)** | ⚠️ **DEVIATION** | **Justified**: Feature implements OAuth 2.1 Resource Server (token validation) rather than GitHub OAuth. This is a valid architectural pattern where authentication is delegated to external Identity Providers. MCP servers acting as resource servers validate bearer tokens from OAuth authorization servers (Google, Microsoft, Auth0, etc.) rather than handling user login directly. |
| **III. Secrets Management (NON-NEGOTIABLE)** | ✅ **COMPLIANT** | Implements Google Cloud Secret Manager for production, .env for development, HTTPS-only enforcement, zero credentials in git |
| **IV. Test-Driven Development (NON-NEGOTIABLE)** | ✅ **COMPLIANT** | TDD approach with security-specific tests before implementation (algorithm confusion tests, rate limit tests, token logging tests) |
| **V. Structured Result Handling** | ✅ **COMPLIANT** | Not applicable - this is authentication middleware, not MCP tools. Token verification returns `AccessToken` objects per FastMCP AuthProvider interface |
| **VI. Cloud Run Production Standards** | ✅ **COMPLIANT** | Service account IAM for Secret Manager, environment-based config, Cloud Logging integration |
| **VII. Progress Transparency** | ✅ **COMPLIANT** | Not applicable - token verification is sub-second operation, no progress reporting needed |
| **VIII. Python & Pydantic Standards** | ✅ **COMPLIANT** | Python 3.11+, Pydantic v2 for all models, SecretStr for sensitive data, type hints throughout |

### Deviation Justification

**Deviation**: Not using GitHub OAuth (Principle II)

**Why Needed**: OAuth 2.1 Resource Server pattern is industry-standard architecture where:
1. **Separation of Concerns**: Authorization Server (identity provider) handles user authentication; Resource Server (this MCP server) only validates tokens
2. **Enterprise Integration**: Enables integration with enterprise identity providers (Google Workspace, Microsoft Entra ID, Okta, Auth0)
3. **MCP 2025 Compliance**: MCP specification mandates resource server pattern, not embedded authorization
4. **Security Benefits**: Centralizes authentication logic in dedicated identity infrastructure with security teams' oversight

**Alternative Rejected**: Implementing GitHub OAuth for MCP tool access was rejected because:
- MCP 2025 specification explicitly requires OAuth 2.1 Resource Server pattern
- Enterprise deployments require integration with corporate identity providers (not GitHub)
- Mixing user authentication (GitHub) with API authentication (bearer tokens) creates confusion
- GitHub OAuth is appropriate for server-to-server scenarios, not for validating client access tokens

**Compliance Note**: This feature still respects the spirit of Principle II (secure authentication) by implementing rigorous OAuth 2.1 token validation with algorithm confusion protection, rate limiting, and comprehensive security hardening.

## Project Structure

### Documentation (this feature)

```
specs/011-mcp-oauth21-security/
├── spec.md                    # Feature specification (complete)
├── plan.md                    # This file (/speckit.plan command output)
├── research.md                # Phase 0: Technology research and decisions
├── data-model.md              # Phase 1: Pydantic models and data structures
├── quickstart.md              # Phase 1: Deployment and configuration guide
├── checklists/
│   └── requirements.md        # Specification quality checklist (complete)
└── contracts/                 # Phase 1: API contracts (if applicable)
```

### Source Code (repository root)

**Existing Structure** (to be enhanced):
```
src/
├── auth/                      # Token verification module (EXISTS - will enhance)
│   ├── __init__.py           # Public API exports (EXISTS - will update)
│   ├── base.py               # TokenVerifier abstract class (EXISTS - will enhance with rate limiting)
│   ├── jwt.py                # JWTVerifier implementation (EXISTS - will fix algorithm confusion)
│   ├── introspection.py      # IntrospectionTokenVerifier (EXISTS - will add SecretStr)
│   ├── fastmcp_adapter.py    # FastMCP AuthProvider integration (EXISTS - already fixed AccessToken)
│   ├── config.py             # Environment configuration loading (EXISTS)
│   ├── rate_limiter.py       # NEW: Token bucket rate limiter
│   └── secrets.py            # NEW: Google Secret Manager integration
├── models/
│   ├── __init__.py
│   └── auth.py               # Authentication models (EXISTS - will enhance with SecretStr)
└── server.py                  # FastMCP server entry point (EXISTS)

tests/
├── unit/
│   ├── test_token_verification_basic.py  # EXISTS (5 tests passing)
│   ├── test_algorithm_confusion.py       # NEW: Security tests
│   ├── test_rate_limiting.py             # NEW: Rate limit tests
│   ├── test_token_logging.py             # NEW: Verify token hashing in logs
│   ├── test_secret_manager.py            # NEW: Secret Manager integration tests
│   └── test_https_enforcement.py         # NEW: HTTPS validation tests
├── integration/
│   └── test_oauth21_compliance.py        # NEW: MCP 2025 spec compliance tests
└── security/
    └── test_security_audit_fixes.py      # NEW: Verify all audit findings fixed

scripts/
└── deploy/
    └── setup_secrets.sh                   # NEW: Script to configure Secret Manager
```

**Structure Decision**: Single project structure maintained. This is authentication middleware that enhances the existing FastMCP server. No new projects or services needed. All changes are within existing `src/auth/` module with two new files (`rate_limiter.py`, `secrets.py`) and comprehensive test coverage.

## Complexity Tracking

*No constitution violations requiring justification. OAuth 2.1 Resource Server pattern deviation is explicitly justified above.*

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| OAuth 2.1 Resource Server (not GitHub OAuth) | MCP 2025 spec mandates resource server pattern for token validation | GitHub OAuth insufficient for enterprise identity integration; MCP clients expect bearer token authentication per OAuth 2.1 |

