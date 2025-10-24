# Tasks: Token Verification

**Input**: Design documents from `/specs/010-token-verification/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: This feature follows TDD (Test-Driven Development) as mandated by the constitution. All tests MUST be written first and verified to fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Project Structure**: Single project with `src/` and `tests/` at repository root
- All new code in `src/auth/` module
- All new tests in `tests/unit/` and `tests/integration/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and directory structure

- [ ] T001 Add PyJWT, cryptography, and httpx dependencies to pyproject.toml or requirements.txt
- [ ] T002 Create src/auth/ directory structure with __init__.py
- [ ] T003 Create tests/unit/ test files structure for auth module
- [ ] T004 Create tests/fixtures/auth/ directory for test data (keys, tokens, JWKS responses)
- [ ] T005 [P] Install pytest-httpx for HTTP mocking in introspection tests
- [ ] T006 [P] Install pytest-asyncio for async test support

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and base classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models (Foundation for all verifiers)

- [ ] T007 [P] Create TokenClaims model in src/models/auth.py with identity, scopes, metadata fields
- [ ] T008 [P] Create ValidationResult model in src/models/auth.py with success/failure states and error categorization
- [ ] T009 [P] Add custom exception classes in src/auth/base.py: TokenValidationError, SystemAuthError
- [ ] T010 [P] Create TokenVerifier abstract base class in src/auth/base.py with verify() and verify_scopes() methods
- [ ] T011 [P] Implement extract_bearer_token() method in TokenVerifier base class

### Unit Tests for Foundation (TDD - Write First, Verify They Fail)

- [ ] T012 [P] Write unit test for TokenClaims model in tests/unit/test_auth_models.py (identity property, scope checking methods)
- [ ] T013 [P] Write unit test for ValidationResult model in tests/unit/test_auth_models.py (success/failure factory methods)
- [ ] T014 [P] Write unit test for extract_bearer_token() in tests/unit/test_token_verifier_base.py (valid/invalid header formats)

**Checkpoint**: Foundation ready - verify all foundation tests FAIL (red phase). User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Production JWT Token Validation (Priority: P1) 🎯 MVP

**Goal**: Enable production JWT validation with JWKS endpoints for enterprise OAuth providers (Okta, Auth0, Azure AD, Google)

**Independent Test**: Configure server with JWKS endpoint, present valid/invalid tokens, verify signature validation, issuer/audience checks, expiration handling, and graceful JWKS failures

**Story Mapping**:
- FR-001 (JWKS validation), FR-002 (static keys), FR-004 (issuer), FR-005 (audience), FR-006 (expiration)
- FR-017 (JWKS caching), FR-018 (JWKS failure handling), FR-020 (clock skew)

### Tests for User Story 1 (TDD - Write First, Verify They Fail) ⚠️

- [ ] T015 [P] [US1] Write unit test for JWTVerifierConfig in tests/unit/test_jwt_config.py (JWKS URI validation, from_env() loader)
- [ ] T016 [P] [US1] Write unit test for JWKS key caching in tests/unit/test_jwt_verifier.py (cache hit/miss, TTL expiration, stale-while-revalidate)
- [ ] T017 [P] [US1] Write unit test for JWT signature verification in tests/unit/test_jwt_verifier.py (valid signature, invalid signature, expired token)
- [ ] T018 [P] [US1] Write unit test for issuer validation in tests/unit/test_jwt_verifier.py (correct issuer, wrong issuer)
- [ ] T019 [P] [US1] Write unit test for audience validation in tests/unit/test_jwt_verifier.py (correct audience, wrong audience, multiple audiences)
- [ ] T020 [P] [US1] Write unit test for clock skew tolerance in tests/unit/test_jwt_verifier.py (60-second default, expired within skew, future tokens within skew)
- [ ] T021 [P] [US1] Write integration test for end-to-end JWT validation in tests/integration/test_jwt_integration.py (mock JWKS endpoint, valid token flow, invalid token rejection)

### Implementation for User Story 1

- [ ] T022 [P] [US1] Create JWTVerifierConfig model in src/models/auth.py with JWKS URI, issuer, audience, algorithm, required_scopes, clock_skew, jwks_cache_ttl fields
- [ ] T023 [P] [US1] Add Pydantic validators to JWTVerifierConfig in src/models/auth.py (mutually exclusive JWKS URI vs public_key check)
- [ ] T024 [P] [US1] Implement JWTVerifierConfig.from_env() class method in src/models/auth.py (load from FASTMCP_SERVER_AUTH_JWT_* environment variables)
- [ ] T025 [US1] Implement JWTVerifier class in src/auth/jwt.py with JWKS endpoint support (using PyJWT's PyJWKClient)
- [ ] T026 [US1] Implement JWKS key caching in src/auth/jwt.py (TTL-based cache with stale-while-revalidate pattern)
- [ ] T027 [US1] Implement JWT signature verification in src/auth/jwt.py (verify() method using PyJWT decode with algorithm enforcement)
- [ ] T028 [US1] Implement issuer claim validation in src/auth/jwt.py (check iss claim matches expected issuer)
- [ ] T029 [US1] Implement audience claim validation in src/auth/jwt.py (check aud claim matches expected audience, handle single string and list)
- [ ] T030 [US1] Implement expiration and clock skew handling in src/auth/jwt.py (use PyJWT leeway parameter for 60-second tolerance)
- [ ] T031 [US1] Implement JWKS endpoint failure handling in src/auth/jwt.py (graceful degradation with cached keys, fail closed on validation errors)
- [ ] T032 [US1] Add logging for JWT validation events in src/auth/jwt.py (validation success, failures, JWKS fetches, cache hits/misses)
- [ ] T033 [US1] Implement scope validation in src/auth/jwt.py (verify_scopes() method checking required scopes against token scopes)

**Checkpoint**: Run all User Story 1 tests - they should now PASS (green phase). JWT validation with JWKS endpoints is fully functional and independently testable.

---

## Phase 4: User Story 2 - Internal Microservice Token Validation (Priority: P1)

**Goal**: Enable HMAC symmetric key validation for internal microservices without complex PKI infrastructure

**Independent Test**: Configure server with shared HMAC secret, present HMAC-signed tokens, verify signature validation and expiration checking

**Story Mapping**:
- FR-003 (HMAC validation), FR-019 (HMAC key length validation)

### Tests for User Story 2 (TDD - Write First, Verify They Fail) ⚠️

- [ ] T034 [P] [US2] Write unit test for HMAC key length validation in tests/unit/test_jwt_config.py (HS256/384/512 minimum lengths, validation error for short keys)
- [ ] T035 [P] [US2] Write unit test for HMAC signature verification in tests/unit/test_jwt_verifier.py (valid HMAC signature, wrong secret rejection)
- [ ] T036 [P] [US2] Write integration test for HMAC token validation in tests/integration/test_jwt_integration.py (end-to-end HMAC flow with HS256/HS384/HS512)

### Implementation for User Story 2

- [ ] T037 [US2] Add HMAC key length validator to JWTVerifierConfig in src/models/auth.py (validate_hmac_key_length model validator checking minimum 32/48/64 bytes)
- [ ] T038 [US2] Extend JWTVerifier in src/auth/jwt.py to support HMAC algorithms (HS256, HS384, HS512 using symmetric public_key)
- [ ] T039 [US2] Implement HMAC signature verification in src/auth/jwt.py (verify() method with symmetric key validation)
- [ ] T040 [US2] Add HMAC-specific error handling in src/auth/jwt.py (clear error messages for weak keys, wrong algorithm)

**Checkpoint**: Run all User Story 2 tests - they should now PASS (green phase). HMAC validation is fully functional and works independently of JWKS-based validation.

---

## Phase 5: User Story 3 - Opaque Token Validation via Introspection (Priority: P2)

**Goal**: Enable OAuth 2.0 Token Introspection (RFC 7662) for opaque tokens with immediate revocation support

**Independent Test**: Configure server with introspection endpoint and client credentials, present opaque tokens, verify introspection HTTP requests, active status checking, scope validation, and graceful endpoint failures

**Story Mapping**:
- FR-007 (introspection), FR-008 (client credentials auth), FR-009 (scope validation for introspection)

### Tests for User Story 3 (TDD - Write First, Verify They Fail) ⚠️

- [ ] T041 [P] [US3] Write unit test for IntrospectionVerifierConfig in tests/unit/test_introspection_config.py (URL validation, client credentials, from_env() loader)
- [ ] T042 [P] [US3] Write unit test for introspection HTTP request in tests/unit/test_introspection_verifier.py (HTTP POST with Basic Auth, form-encoded token parameter, using pytest-httpx mocks)
- [ ] T043 [P] [US3] Write unit test for introspection response parsing in tests/unit/test_introspection_verifier.py (active=true, active=false, scope extraction, token metadata)
- [ ] T044 [P] [US3] Write unit test for introspection endpoint failure handling in tests/unit/test_introspection_verifier.py (timeout, network error, invalid response format)
- [ ] T045 [P] [US3] Write integration test for end-to-end introspection in tests/integration/test_introspection_integration.py (mock introspection endpoint, active token acceptance, revoked token rejection)

### Implementation for User Story 3

- [ ] T046 [P] [US3] Create IntrospectionVerifierConfig model in src/models/auth.py with introspection_url, client_id, client_secret, required_scopes, timeout fields
- [ ] T047 [P] [US3] Add HTTPS URL validator to IntrospectionVerifierConfig in src/models/auth.py (validate introspection_url uses HTTPS except localhost)
- [ ] T048 [P] [US3] Implement IntrospectionVerifierConfig.from_env() in src/models/auth.py (load from FASTMCP_SERVER_AUTH_INTROSPECTION_* environment variables)
- [ ] T049 [US3] Implement IntrospectionTokenVerifier class in src/auth/introspection.py (inherit from TokenVerifier base class)
- [ ] T050 [US3] Implement introspection HTTP request in src/auth/introspection.py (POST to introspection_url with httpx AsyncClient, HTTP Basic Auth with client credentials)
- [ ] T051 [US3] Implement introspection response parsing in src/auth/introspection.py (parse RFC 7662 response, extract active status, scopes, expiration, subject)
- [ ] T052 [US3] Implement introspection response validation in src/auth/introspection.py (verify active=true, map introspection claims to TokenClaims)
- [ ] T053 [US3] Implement introspection endpoint failure handling in src/auth/introspection.py (timeout handling, network error handling, fail closed on errors)
- [ ] T054 [US3] Implement scope validation for introspection in src/auth/introspection.py (verify_scopes() method checking required scopes)
- [ ] T055 [US3] Add logging for introspection events in src/auth/introspection.py (introspection requests, active/inactive results, errors, latency)

**Checkpoint**: Run all User Story 3 tests - they should now PASS (green phase). Opaque token introspection is fully functional and works independently of JWT validation.

---

## Phase 6: User Story 4 - Development Environment Token Testing (Priority: P3)

**Goal**: Provide static token verification and RSA key pair generation utilities for rapid local development without external OAuth infrastructure

**Independent Test**: Configure server with static token mapping, present predefined tokens, verify claim loading. Generate RSA key pair, create test tokens, verify signature validation works.

**Story Mapping**:
- FR-010 (static tokens), FR-011 (RSA key pair generation)

### Tests for User Story 4 (TDD - Write First, Verify They Fail) ⚠️

- [ ] T056 [P] [US4] Write unit test for StaticTokenVerifierConfig in tests/unit/test_static_config.py (token mapping validation, production environment check)
- [ ] T057 [P] [US4] Write unit test for static token lookup in tests/unit/test_static_verifier.py (valid token, invalid token, claim extraction)
- [ ] T058 [P] [US4] Write unit test for RSAKeyPair generation in tests/unit/test_rsa_keypair.py (key generation, PEM export, JWKS export)
- [ ] T059 [P] [US4] Write unit test for RSAKeyPair token creation in tests/unit/test_rsa_keypair.py (create_token() method, subject/issuer/audience/scopes/expiration)
- [ ] T060 [P] [US4] Write integration test for static token development workflow in tests/integration/test_static_integration.py (static tokens with predefined claims, access control based on scopes)
- [ ] T061 [P] [US4] Write integration test for RSA key pair test workflow in tests/integration/test_rsa_integration.py (generate key pair, create token, verify with JWTVerifier)

### Implementation for User Story 4

- [ ] T062 [P] [US4] Create StaticTokenVerifierConfig model in src/models/auth.py with tokens dict, required_scopes fields
- [ ] T063 [P] [US4] Add production environment check to StaticTokenVerifierConfig in src/models/auth.py (prevent_production_use validator raising ValueError if ENVIRONMENT=production)
- [ ] T064 [P] [US4] Add token claims validator to StaticTokenVerifierConfig in src/models/auth.py (validate_token_claims ensuring each token has client_id or subject)
- [ ] T065 [US4] Implement StaticTokenVerifier class in src/auth/jwt.py (inherit from TokenVerifier, simple dict lookup)
- [ ] T066 [US4] Implement static token lookup in src/auth/jwt.py (verify() method with dictionary-based token-to-claims mapping)
- [ ] T067 [US4] Implement RSAKeyPair class in src/auth/jwt.py (using cryptography library for RSA key generation)
- [ ] T068 [US4] Implement RSA key generation in src/auth/jwt.py (generate() class method with configurable key_size)
- [ ] T069 [US4] Implement PEM export methods in src/auth/jwt.py (private_key_pem and public_key_pem properties)
- [ ] T070 [US4] Implement JWKS export in src/auth/jwt.py (to_jwks() method converting RSA public key to JWK format)
- [ ] T071 [US4] Implement test token creation in src/auth/jwt.py (create_token() method with subject, issuer, audience, scopes, expiration parameters)
- [ ] T072 [US4] Add development utility logging in src/auth/jwt.py (warnings for static token usage, key generation events)

**Checkpoint**: Run all User Story 4 tests - they should now PASS (green phase). Development utilities are fully functional for rapid local testing.

---

## Phase 7: User Story 5 - Environment-Based Configuration (Priority: P2)

**Goal**: Enable server configuration via environment variables for deployment flexibility across development, staging, and production environments

**Independent Test**: Set environment variables for JWT/introspection settings, start server without programmatic configuration, verify authentication behavior matches environment settings

**Story Mapping**:
- FR-012 (environment variable configuration)

### Tests for User Story 5 (TDD - Write First, Verify They Fail) ⚠️

- [ ] T073 [P] [US5] Write unit test for JWTVerifierConfig.from_env() in tests/unit/test_jwt_config.py (load all FASTMCP_SERVER_AUTH_JWT_* variables, defaults for optional settings)
- [ ] T074 [P] [US5] Write unit test for IntrospectionVerifierConfig.from_env() in tests/unit/test_introspection_config.py (load all FASTMCP_SERVER_AUTH_INTROSPECTION_* variables)
- [ ] T075 [P] [US5] Write integration test for multi-environment config in tests/integration/test_env_config.py (set different env vars, verify server behavior changes)
- [ ] T076 [P] [US5] Write integration test for config validation errors in tests/integration/test_env_config.py (invalid URLs, missing required variables, malformed values)

### Implementation for User Story 5

- [ ] T077 [US5] Create config loader module in src/auth/config.py with load_auth_config_from_env() function
- [ ] T078 [US5] Implement automatic verifier selection in src/auth/config.py (detect FASTMCP_SERVER_AUTH variable to choose JWT vs introspection)
- [ ] T079 [US5] Add config validation in src/auth/config.py (validate required environment variables are set, provide helpful error messages)
- [ ] T080 [US5] Implement config caching in src/auth/config.py (cache loaded config to avoid repeated environment variable reads)
- [ ] T081 [US5] Add config logging in src/auth/config.py (log loaded configuration at server startup, mask secrets in logs)
- [ ] T082 [US5] Create config documentation comment in src/auth/config.py (document all FASTMCP_SERVER_AUTH_* environment variables)

**Checkpoint**: Run all User Story 5 tests - they should now PASS (green phase). Environment-based configuration is fully functional for deployment flexibility.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, logging, documentation, and integration verification

**⚠️ Cross-Story**: These tasks span multiple user stories and should be done after core functionality is complete

### Error Handling & Logging

- [ ] T083 [P] Implement comprehensive error messages in src/auth/base.py (user-friendly messages for common errors, mask internal details)
- [ ] T084 [P] Add structured logging for all verifiers in src/auth/__init__.py (validation success/failure, performance metrics, security events)
- [ ] T085 [P] Implement error masking in production in src/auth/base.py (prevent sensitive information leakage in error messages)

### Edge Case Handling

- [ ] T086 [P] Handle malformed JWT tokens in src/auth/jwt.py (cannot parse, invalid base64, missing segments)
- [ ] T087 [P] Handle missing identity claims in src/auth/jwt.py (no subject or client_id in token)
- [ ] T088 [P] Handle missing scope claims when scopes required in src/auth/jwt.py (token has no scope claim but scopes are required)
- [ ] T089 [P] Handle non-conforming introspection responses in src/auth/introspection.py (missing active field, unexpected format)
- [ ] T090 [P] Handle concurrent JWKS key rotation in src/auth/jwt.py (support multiple simultaneous keys via kid matching)
- [ ] T091 [P] Handle future-issued tokens within clock skew in src/auth/jwt.py (iat in future but within leeway)
- [ ] T092 [P] Handle multiple Authorization headers in src/auth/base.py (reject requests with multiple auth headers)

### Test Fixtures & Test Helpers

- [ ] T093 [P] Create test fixtures in tests/fixtures/auth/test_tokens.py (sample valid/invalid tokens for all algorithms)
- [ ] T094 [P] Create test JWKS responses in tests/fixtures/auth/mock_jwks.json (sample JWKS with multiple keys, kid matching)
- [ ] T095 [P] Create test introspection responses in tests/fixtures/auth/mock_introspection.json (active/inactive responses, various metadata)
- [ ] T096 [P] Create pytest fixtures for common test setup in tests/conftest.py (mock JWKS server, mock introspection endpoint, test key pairs)

### Integration Testing

- [ ] T097 Create end-to-end integration test in tests/integration/test_full_auth_flow.py (combine multiple auth methods, verify all user stories work together)
- [ ] T098 Create performance test in tests/integration/test_performance.py (verify <100ms JWT validation, <200ms introspection p95)
- [ ] T099 Create security test in tests/integration/test_security.py (verify fail-closed behavior, proper error masking, no information leakage)

### Documentation

- [ ] T100 [P] Add docstrings to all public methods in src/auth/ module (comprehensive API documentation)
- [ ] T101 [P] Add type hints to all functions in src/auth/ module (full type coverage for IDE support)
- [ ] T102 [P] Update src/auth/__init__.py to export public API (JWTVerifier, IntrospectionTokenVerifier, StaticTokenVerifier, RSAKeyPair, config models)

### Refactoring (Optional - Only if TDD reveals duplicates)

- [ ] T103 Extract common validation logic if duplicated across verifiers in src/auth/base.py
- [ ] T104 Refactor error handling if patterns emerge across verifiers in src/auth/base.py

---

## Dependencies & Parallel Execution

### User Story Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational Models & Base Classes) ← MUST complete before any user story
    ↓
    ├─→ Phase 3: US1 (JWT w/ JWKS) ─────── Can run in parallel ───┐
    ├─→ Phase 4: US2 (HMAC)         ─────── Can run in parallel ───┤
    ├─→ Phase 5: US3 (Introspection) ─────── Can run in parallel ───├─→ Phase 8 (Polish)
    ├─→ Phase 6: US4 (Dev Utilities) ─────── Can run in parallel ───┤
    └─→ Phase 7: US5 (Env Config)    ─────── Can run in parallel ───┘
```

### Parallel Execution Examples

**After Phase 2 completes, these can run simultaneously:**

**Team A**: US1 (JWT with JWKS)
```bash
# Tasks T015-T033 can be assigned to Team A
# Tests first (T015-T021), then implementation (T022-T033)
```

**Team B**: US2 (HMAC Validation)
```bash
# Tasks T034-T040 can be assigned to Team B
# Tests first (T034-T036), then implementation (T037-T040)
```

**Team C**: US3 (Introspection)
```bash
# Tasks T041-T055 can be assigned to Team C
# Tests first (T041-T045), then implementation (T046-T055)
```

**Team D**: US4 (Dev Utilities)
```bash
# Tasks T056-T072 can be assigned to Team D
# Tests first (T056-T061), then implementation (T062-T072)
```

**Team E**: US5 (Environment Config)
```bash
# Tasks T073-T082 can be assigned to Team E
# Tests first (T073-T076), then implementation (T077-T082)
```

### Critical Path

**Sequential (Cannot parallelize):**
1. Phase 1: Setup (T001-T006)
2. Phase 2: Foundation (T007-T014)
3. Phase 8: Polish & Integration (T083-T104) - requires all user stories complete

**Total Duration Estimate** (with 5 parallel teams):
- Phase 1: 1 day
- Phase 2: 2 days
- Phase 3-7 (parallel): 5 days (longest user story path)
- Phase 8: 2 days
- **Total: ~10 days with parallel execution** vs ~25 days sequential

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Recommended MVP**: User Story 1 ONLY (Production JWT with JWKS)

**Rationale**:
- Delivers core security value for production deployments
- Covers most common enterprise use case (OAuth providers)
- Enables immediate integration with Okta, Auth0, Azure AD, Google
- Fully testable independently
- Can be shipped and deliver value before other stories

**MVP Tasks**: T001-T033 (Setup + Foundation + US1)
- **Duration**: ~4 days with one team
- **Deliverable**: Functional JWT validation with JWKS endpoints

### Incremental Delivery Plan

**Release 1 (MVP)**: US1 - Production JWT validation
- Tasks: T001-T033
- Value: Enterprise OAuth integration

**Release 2**: US1 + US2 - Add HMAC for microservices
- Tasks: T034-T040
- Value: Internal service authentication

**Release 3**: US1 + US2 + US5 - Add environment config
- Tasks: T073-T082
- Value: Multi-environment deployments

**Release 4**: US1 + US2 + US5 + US3 - Add introspection
- Tasks: T041-T055
- Value: Opaque token support

**Release 5 (Complete)**: All user stories + polish
- Tasks: T001-T104
- Value: Full feature set with development utilities

---

## Summary

**Total Tasks**: 104
- Setup: 6 tasks
- Foundational: 8 tasks
- User Story 1 (P1): 19 tasks (7 tests + 12 implementation)
- User Story 2 (P1): 7 tasks (3 tests + 4 implementation)
- User Story 3 (P2): 15 tasks (5 tests + 10 implementation)
- User Story 4 (P3): 17 tasks (6 tests + 11 implementation)
- User Story 5 (P2): 10 tasks (4 tests + 6 implementation)
- Polish & Cross-Cutting: 22 tasks

**Parallel Opportunities**:
- 5 user stories can be implemented in parallel after foundation (US1, US2, US3, US4, US5)
- Within each story: Most tasks marked [P] can run in parallel (different files)
- Estimated 60% time savings with parallel execution (10 days vs 25 days)

**Independent Test Criteria**:
- **US1**: Configure JWKS endpoint, verify token validation and rejection scenarios
- **US2**: Configure HMAC secret, verify symmetric key validation
- **US3**: Configure introspection endpoint, verify opaque token validation
- **US4**: Use static tokens and key generation, verify development workflows
- **US5**: Set environment variables, verify configuration loading

**MVP Recommendation**: US1 only (T001-T033) - 33 tasks delivering core production value

**TDD Approach**: All test tasks MUST be written first and verified to FAIL before implementation begins (constitution requirement)

**Format Validation**: ✅ All 104 tasks follow checklist format with ID, [P] marker (where applicable), [Story] label (for user story tasks), and file paths
