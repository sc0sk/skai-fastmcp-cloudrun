# Implementation Plan: Token Verification

**Branch**: `010-token-verification` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-token-verification/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Token Verification enables FastMCP servers to act as OAuth resource servers by validating bearer tokens issued by external authentication systems. The feature implements JWT verification (JWKS endpoints, static public keys, HMAC symmetric keys), opaque token validation via OAuth 2.0 Token Introspection (RFC 7662), development utilities (static tokens, RSA key pair generation), and environment-based configuration for deployment flexibility.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (Cloud Run compatibility requirement)
**Primary Dependencies**: PyJWT (JWT validation), cryptography (RSA/ECDSA keys), httpx (HTTP introspection), Pydantic v2 (schemas), FastMCP 2.12.0+ (auth provider framework)
**Storage**: N/A (stateless token validation, no persistent storage required)
**Testing**: pytest with async support, pytest-httpx (mock HTTP introspection), pytest-asyncio
**Target Platform**: Linux server (Google Cloud Run, local development environments)
**Project Type**: Single project (server-side authentication library)
**Performance Goals**: <100ms JWT validation with cached JWKS keys, <200ms token introspection (p95), 10,000+ concurrent request capacity
**Constraints**: <50ms validation overhead, graceful degradation on JWKS endpoint failures, zero request drops during key rotation, 60-second clock skew tolerance
**Scale/Scope**: Enterprise deployment scale (multi-tenant OAuth providers, high-throughput microservices), 5 verifier classes, 10+ test scenarios per verifier

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Compliance

| Principle | Status | Notes |
|-----------|---------|-------|
| **I. FastMCP Server-First** | ✅ PASS | Feature enhances server security without adding new MCP tools - it's infrastructure for existing tools |
| **II. Secure Authentication** | ⚠️ DEVIATION | Feature provides **alternative** to GitHub OAuth (token verification instead). This is intentional - enables integration with existing enterprise auth systems |
| **III. Secrets Management** | ✅ PASS | All token verification settings configurable via environment variables (FASTMCP_SERVER_AUTH_JWT_*, FASTMCP_SERVER_AUTH_INTROSPECTION_*) |
| **IV. Test-Driven Development** | ✅ PASS | TDD mandatory for all verifier classes - unit tests for validation logic, integration tests for end-to-end flows |
| **V. Structured Result Handling** | ✅ PASS | Token verification returns structured validation results with claims data, but this is server infrastructure not tool results |
| **VI. Cloud Run Production** | ✅ PASS | Environment-based configuration supports Cloud Run deployment patterns (secrets, env vars, health checks) |
| **VII. Progress Transparency** | ✅ PASS | Token validation is fast (<100ms) - no progress reporting needed |
| **VIII. Python & Pydantic** | ✅ PASS | Python 3.11+, Pydantic v2 for token claims and configuration models, uv for dependency management |
| **IX. ChatGPT Integration** | ✅ PASS | Token verification enables secure ChatGPT integration without GitHub OAuth dependency |
| **X. MCP JSON Configuration** | ✅ PASS | No changes to MCP JSON format - auth configuration via environment variables |
| **XI. Tool Implementation** | ✅ PASS | No new tools added - feature is authentication infrastructure |

### Authentication Deviation Justification

**Deviation**: Feature provides token verification as alternative to GitHub OAuth (Principle II)

**Why Needed**:
- Enterprise deployments often have existing OAuth/OIDC identity providers (Okta, Auth0, Azure AD, internal systems)
- GitHub OAuth is excellent for GitHub-centric workflows but not suitable for enterprise single sign-on scenarios
- Many organizations require integration with existing authentication infrastructure
- Token verification enables MCP servers to integrate into microservices architectures with existing auth patterns

**Simpler Alternative Rejected**:
- "Use GitHub OAuth exclusively": Rejected because enterprise customers cannot integrate MCP servers into existing identity management systems
- "Each organization runs separate GitHub OAuth app": Rejected because this creates proliferation of OAuth apps and doesn't leverage existing identity infrastructure
- "No authentication": Rejected because this violates security requirements

**Coexistence Strategy**: Token verification and GitHub OAuth can coexist - servers can support multiple auth providers. This feature **adds** token verification as an option, it doesn't **replace** GitHub OAuth.

### Gates Status

✅ **PASS** - Proceed to Phase 0 Research

**Rationale**: The authentication deviation is justified and intentional. Token verification addresses a real enterprise need (integration with existing identity providers) while maintaining all other constitution principles. The feature enhances FastMCP's flexibility for enterprise deployments without compromising security standards.

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
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
src/
├── auth/                           # NEW: Authentication and token verification
│   ├── __init__.py
│   ├── base.py                     # NEW: Base TokenVerifier abstract class
│   ├── jwt.py                      # NEW: JWTVerifier, StaticTokenVerifier, RSAKeyPair
│   ├── introspection.py            # NEW: IntrospectionTokenVerifier
│   └── config.py                   # NEW: Environment-based configuration loader
├── models/                         # Existing: Pydantic models
│   └── auth.py                     # NEW: Token claims, validation result models
├── tools/                          # Existing: MCP tools
├── storage/                        # Existing: Database layer
├── utils/                          # Existing: Utilities
└── server.py                       # Existing: FastMCP server entrypoint

tests/
├── unit/                           # Existing: Unit tests
│   ├── test_jwt_verifier.py        # NEW: JWT verification tests
│   ├── test_introspection.py       # NEW: Introspection tests
│   └── test_token_config.py        # NEW: Configuration tests
├── integration/                    # Existing: Integration tests
│   └── test_auth_integration.py    # NEW: End-to-end auth flow tests
└── fixtures/                       # Existing: Test fixtures
    └── auth/                       # NEW: Test tokens, keys, mock JWKS
```

**Structure Decision**: Single project structure following existing conventions. New `src/auth/` module contains all token verification logic with sub-modules for JWT (including HMAC and static verification), introspection, and configuration. Authentication models live in `src/models/auth.py` following existing patterns. Tests follow existing unit/integration split with new auth-specific test files.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**No violations requiring justification** - The authentication deviation (Principle II) is justified above in the Constitution Check section.

## Phase 0: Research (Completed)

✅ **research.md** - Comprehensive research on:
- JWT validation libraries (PyJWT selected)
- Token introspection protocols (httpx + RFC 7662)
- JWKS key caching strategies (time-based cache with stale-while-revalidate)
- Clock skew tolerance (60-second default)
- HMAC key length requirements (32/48/64 bytes by algorithm)
- Error handling patterns (401 validation vs 500 system errors)
- Development testing utilities (StaticTokenVerifier, RSAKeyPair)
- Environment-based configuration (FASTMCP_SERVER_AUTH_* prefix)
- Security best practices and OWASP compliance
- Performance benchmarks and optimization strategies

All technical unknowns resolved. No blockers for implementation.

## Phase 1: Design & Contracts (Completed)

✅ **data-model.md** - Pydantic v2 data models:
- `TokenClaims` - Validated token claims with scope checking methods
- `ValidationResult` - Success/failure result with error categorization
- `JWTVerifierConfig` - JWT verification configuration with HMAC key validation
- `IntrospectionVerifierConfig` - OAuth 2.0 introspection configuration
- `StaticTokenVerifierConfig` - Development-only static token mapping
- `TokenVerifier` - Abstract base class for all verifier implementations
- `RSAKeyPair` - Test key generation utility

✅ **quickstart.md** - Five deployment scenarios:
1. Production JWT with JWKS endpoints (Okta, Auth0, Azure AD, Google)
2. HMAC symmetric keys (internal microservices)
3. Static public keys (fixed RSA/ECDSA environments)
4. OAuth token introspection (opaque tokens, RFC 7662)
5. Development testing (static tokens, test key generation)

Each scenario includes: setup steps, code examples, testing guidance, troubleshooting, Cloud Run deployment.

✅ **Agent context updated** - CLAUDE.md updated with:
- Python 3.11+ (Cloud Run compatibility)
- PyJWT, cryptography, httpx, Pydantic v2
- Token verification as server infrastructure (not MCP tools)
- Feature #010 documented in technology stack

❌ **contracts/** - Not applicable (authentication infrastructure, not API contracts)

## Constitution Check Re-evaluation (Post-Design)

| Principle | Status | Post-Design Notes |
|-----------|---------|-------------------|
| **I. FastMCP Server-First** | ✅ PASS | No tools added - verified in design phase |
| **II. Secure Authentication** | ⚠️ DEVIATION (justified) | Token verification adds auth flexibility while maintaining security standards |
| **III. Secrets Management** | ✅ PASS | All config via env vars, Cloud Run secrets integration documented |
| **IV. Test-Driven Development** | ✅ PASS | Comprehensive test scenarios in quickstart.md, ready for TDD implementation |
| **V. Structured Result Handling** | ✅ PASS | ValidationResult model provides structured success/failure with detailed errors |
| **VI. Cloud Run Production** | ✅ PASS | Environment-based config, secrets management, deployment scenarios documented |
| **VII. Progress Transparency** | ✅ PASS | Token validation <100ms - no progress reporting needed |
| **VIII. Python & Pydantic** | ✅ PASS | All models use Pydantic v2, Python 3.11+ dependencies specified |
| **IX. ChatGPT Integration** | ✅ PASS | Token verification enables secure ChatGPT access without GitHub OAuth lock-in |
| **X. MCP JSON Configuration** | ✅ PASS | Environment-based config compatible with all MCP clients |
| **XI. Tool Implementation** | ✅ PASS | No tools - authentication infrastructure only |

### Final Gates Status

✅ **PASS** - Ready for Phase 2 (tasks.md generation via `/speckit.tasks`)

**Design Validation**:
- All data models specify Pydantic v2 with comprehensive validation rules
- All security requirements addressed (clock skew, HMAC key lengths, fail-closed errors)
- All performance targets documented (<100ms JWT, <200ms introspection)
- All deployment scenarios covered (production, development, testing)
- No constitution violations beyond justified authentication deviation

**Next Command**: `/speckit.tasks` to generate dependency-ordered implementation tasks

