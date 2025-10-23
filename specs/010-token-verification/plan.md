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

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

