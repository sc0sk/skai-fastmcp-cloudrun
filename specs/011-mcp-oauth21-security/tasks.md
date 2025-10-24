# Tasks: MCP OAuth 2.1 Compliance and Security Hardening

**Input**: Design documents from `/specs/011-mcp-oauth21-security/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: TDD approach per project constitution - all test tasks are included and must be completed BEFORE implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5, US6)
- All file paths are relative to repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [ ] T001 Add new dependencies to pyproject.toml (google-cloud-secret-manager>=2.16.0, python-dotenv>=1.0.0)
- [ ] T002 Install dependencies with uv pip install
- [ ] T003 [P] Create src/auth/rate_limiter.py skeleton file
- [ ] T004 [P] Create src/auth/secrets.py skeleton file
- [ ] T005 [P] Create tests/unit/test_algorithm_confusion.py skeleton
- [ ] T006 [P] Create tests/unit/test_rate_limiting.py skeleton
- [ ] T007 [P] Create tests/unit/test_token_logging.py skeleton
- [ ] T008 [P] Create tests/unit/test_secret_manager.py skeleton
- [ ] T009 [P] Create tests/unit/test_https_enforcement.py skeleton
- [ ] T010 [P] Create tests/integration/test_oauth21_compliance.py skeleton
- [ ] T011 [P] Create tests/security/test_security_audit_fixes.py skeleton
- [ ] T012 [P] Create scripts/deploy/setup_secrets.sh script skeleton

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core security infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Enhanced Configuration Models

- [ ] T013 [P] Update TokenClaims model in src/models/auth.py to add is_expired() and is_not_yet_valid() methods
- [ ] T014 [P] Update ValidationResult model in src/models/auth.py to ensure success_result() and failure_result() class methods exist
- [ ] T015 Add SecretStr import from pydantic to src/models/auth.py

### Token Hash Utility

- [ ] T016 Create hash_token() utility function in src/auth/base.py using hashlib.sha256 (returns first 16 chars of hex digest)
- [ ] T017 [P] Write unit test for hash_token() in tests/unit/test_token_logging.py verifying same token produces same hash and different tokens produce different hashes

### Rate Limiter Infrastructure

- [ ] T018 Create RateLimitConfig model in src/auth/rate_limiter.py with max_attempts (default 10), window_seconds (default 60), enabled (default True)
- [ ] T019 Create RateLimitBucket model in src/auth/rate_limiter.py with token_hash, attempts list, last_cleanup timestamp
- [ ] T020 Add is_rate_limited(), record_attempt(), cleanup_expired() methods to RateLimitBucket in src/auth/rate_limiter.py

### Secret Manager Infrastructure

- [ ] T021 Create SecretBackend enum in src/auth/secrets.py with values ENV and GCP_SECRET_MANAGER
- [ ] T022 Create SecretConfig model in src/auth/secrets.py with backend, gcp_project_id, cache_ttl_seconds fields
- [ ] T023 Add validate_gcp_config() model validator to SecretConfig in src/auth/secrets.py ensuring gcp_project_id required when backend is GCP_SECRET_MANAGER
- [ ] T024 Create CachedSecret model in src/auth/secrets.py with name, value (SecretStr), cached_at, version fields
- [ ] T025 Add is_expired() and age_seconds property to CachedSecret in src/auth/secrets.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 3 - Algorithm Confusion Protection (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Fix CVE-level algorithm confusion vulnerability by enforcing algorithm whitelist and preventing JWKS+HMAC misconfiguration

**Independent Test**: Create RS256 JWT, modify header to HS256, sign with public key as HMAC secret, verify server rejects with HTTP 401

### Tests for User Story 3 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T026 [P] [US3] Write test_jwks_rejects_hmac_algorithm() in tests/unit/test_algorithm_confusion.py - verify JWKS config with HS256 raises ValidationError
- [ ] T027 [P] [US3] Write test_hmac_rejects_jwks_uri() in tests/unit/test_algorithm_confusion.py - verify HMAC config with jwks_uri raises ValidationError
- [ ] T028 [P] [US3] Write test_asymmetric_algorithms_allowed_with_jwks() in tests/unit/test_algorithm_confusion.py - verify RS256/RS384/RS512/ES256/ES384/ES512 pass validation with JWKS
- [ ] T029 [P] [US3] Write test_algorithm_confusion_attack_rejected() in tests/security/test_security_audit_fixes.py - attempt HS256 attack on RS256 config, verify rejection
- [ ] T030 [P] [US3] Write test_weak_hmac_key_rejected() in tests/unit/test_algorithm_confusion.py - verify keys with repeated chars/test strings are rejected
- [ ] T031 [P] [US3] Write test_short_hmac_key_rejected() in tests/unit/test_algorithm_confusion.py - verify HS256 key <32 bytes rejected, HS384 <48 bytes, HS512 <64 bytes

### Implementation for User Story 3

- [ ] T032 [P] [US3] Add validate_algorithm_safety() model validator to JWTVerifierConfig in src/models/auth.py enforcing SAFE_ASYMMETRIC_ALGORITHMS for JWKS
- [ ] T033 [P] [US3] Add validate_hmac_key_strength() model validator to JWTVerifierConfig in src/models/auth.py checking length, weak patterns, base64 decoding
- [ ] T034 [US3] Update JWTVerifierConfig in src/models/auth.py to change public_key field from str to SecretStr for HMAC keys
- [ ] T035 [US3] Update JWTVerifier in src/auth/jwt.py to use .get_secret_value() when accessing public_key for HMAC verification
- [ ] T036 [US3] Add SAFE_ASYMMETRIC_ALGORITHMS and SAFE_SYMMETRIC_ALGORITHMS constants at top of src/models/auth.py
- [ ] T037 [US3] Run all US3 tests and verify they now pass (pytest tests/unit/test_algorithm_confusion.py tests/security/test_security_audit_fixes.py -v)

**Checkpoint**: Algorithm confusion vulnerability fixed, JWKS+HMAC misconfiguration prevented, weak HMAC keys rejected

---

## Phase 4: User Story 6 - Rate Limiting and Brute Force Protection (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Implement token bucket rate limiting (10 attempts/60s per token hash) to prevent brute force attacks and DoS

**Independent Test**: Send 11 consecutive requests with invalid token within 60 seconds, verify 11th returns HTTP 429

### Tests for User Story 6 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T038 [P] [US6] Write test_rate_limit_blocks_11th_attempt() in tests/unit/test_rate_limiting.py - verify 10 attempts pass, 11th returns HTTP 429
- [ ] T039 [P] [US6] Write test_rate_limit_resets_after_window() in tests/unit/test_rate_limiting.py - verify window reset after 60 seconds
- [ ] T040 [P] [US6] Write test_rate_limit_per_token_hash() in tests/unit/test_rate_limiting.py - verify different tokens have independent limits
- [ ] T041 [P] [US6] Write test_token_hashing_in_logs() in tests/unit/test_token_logging.py - verify only SHA-256 hashes appear in logs, no plaintext tokens
- [ ] T042 [P] [US6] Write test_rate_limiter_memory_bounded() in tests/unit/test_rate_limiting.py - verify automatic cleanup of expired entries
- [ ] T043 [P] [US6] Write test_concurrent_rate_limiting() in tests/unit/test_rate_limiting.py - verify thread-safe operation under concurrent requests

### Implementation for User Story 6

- [ ] T044 [P] [US6] Implement RateLimiter class in src/auth/rate_limiter.py with __init__(config), check_rate_limit(token_hash), cleanup() methods
- [ ] T045 [P] [US6] Add asyncio.Lock to RateLimiter in src/auth/rate_limiter.py for thread-safe concurrent access
- [ ] T046 [P] [US6] Implement automatic cleanup in RateLimiter in src/auth/rate_limiter.py removing entries older than window duration
- [ ] T047 [US6] Add RateLimiter instance to TokenVerifier base class in src/auth/base.py (initialize in __init__)
- [ ] T048 [US6] Update TokenVerifier.verify() in src/auth/base.py to call rate limiter before actual verification
- [ ] T049 [US6] Add rate limit check logic to JWTVerifier.verify() in src/auth/jwt.py using hash_token() and rate limiter
- [ ] T050 [US6] Add rate limit check logic to IntrospectionTokenVerifier.verify() in src/auth/introspection.py
- [ ] T051 [US6] Add rate limit check logic to StaticTokenVerifier.verify() in src/auth/jwt.py
- [ ] T052 [US6] Update all logging statements in src/auth/jwt.py to use hash_token(token) instead of token[:10] or full token
- [ ] T053 [US6] Update all logging statements in src/auth/introspection.py to use hash_token(token)
- [ ] T054 [US6] Update all logging statements in src/auth/fastmcp_adapter.py to use hash_token(token)
- [ ] T055 [US6] Add ValidationResult.failure_result() call for rate limit exceeded returning HTTP 429 with error "rate_limit_exceeded"
- [ ] T056 [US6] Run all US6 tests and verify they now pass (pytest tests/unit/test_rate_limiting.py tests/unit/test_token_logging.py -v)

**Checkpoint**: Rate limiting active, brute force attacks blocked, all tokens hashed in logs

---

## Phase 5: User Story 2 - Secure Secret Management (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Implement Google Cloud Secret Manager integration with TTL caching and .env fallback for development

**Independent Test**: Store secrets in Secret Manager, configure backend=gcp_secret_manager, verify server retrieves and uses secrets without logging them

### Tests for User Story 2 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T057 [P] [US2] Write test_secret_manager_retrieval() in tests/unit/test_secret_manager.py - mock Secret Manager, verify secret fetched
- [ ] T058 [P] [US2] Write test_secret_cache_ttl() in tests/unit/test_secret_manager.py - verify cache hit avoids API call, TTL expiration triggers refetch
- [ ] T059 [P] [US2] Write test_secret_version_support() in tests/unit/test_secret_manager.py - verify "latest" and specific version retrieval
- [ ] T060 [P] [US2] Write test_secret_manager_fallback() in tests/unit/test_secret_manager.py - verify fallback to env vars when Secret Manager unavailable
- [ ] T061 [P] [US2] Write test_secretstr_masking() in tests/unit/test_secret_manager.py - verify str(secret_config) doesn't contain plaintext secrets
- [ ] T062 [P] [US2] Write test_dotenv_loading() in tests/unit/test_secret_manager.py - verify .env file loading in development with warnings

### Implementation for User Story 2

- [ ] T063 [P] [US2] Implement SecretManager class in src/auth/secrets.py with __init__(config), get_secret(name, version), _fetch_from_gcp(), _fetch_from_env() methods
- [ ] T064 [P] [US2] Add cache dict[str, CachedSecret] to SecretManager in src/auth/secrets.py for storing cached secrets
- [ ] T065 [P] [US2] Implement TTL-based cache invalidation in SecretManager.get_secret() in src/auth/secrets.py checking is_expired() before returning cached value
- [ ] T066 [P] [US2] Add google.cloud.secretmanager.SecretManagerServiceClient integration in SecretManager._fetch_from_gcp() in src/auth/secrets.py
- [ ] T067 [P] [US2] Add fallback chain logic to SecretManager.get_secret() in src/auth/secrets.py (try Secret Manager → fallback to env vars → raise error)
- [ ] T068 [P] [US2] Implement .env file loading using python-dotenv in SecretManager.__init__() in src/auth/secrets.py when backend is ENV
- [ ] T069 [US2] Update IntrospectionVerifierConfig in src/models/auth.py to change client_secret from str to SecretStr
- [ ] T070 [US2] Update IntrospectionTokenVerifier in src/auth/introspection.py to use client_secret.get_secret_value() in auth tuple
- [ ] T071 [US2] Add from_env() class method to SecretConfig in src/auth/secrets.py loading FASTMCP_SERVER_AUTH_SECRET_BACKEND, GCP_PROJECT_ID, etc.
- [ ] T072 [US2] Add load_config_from_secrets() helper function in src/auth/config.py using SecretManager to fetch JWT/introspection configuration
- [ ] T073 [US2] Update JWTVerifierConfig.from_env() in src/models/auth.py to support loading from Secret Manager when backend is gcp_secret_manager
- [ ] T074 [US2] Update IntrospectionVerifierConfig.from_env() in src/models/auth.py to support loading from Secret Manager
- [ ] T075 [US2] Run all US2 tests and verify they now pass (pytest tests/unit/test_secret_manager.py -v)

**Checkpoint**: Secret Manager integration complete, secrets never appear in logs, automatic rotation supported

---

## Phase 6: User Story 1 - Secure JWT Token Validation with JWKS (Priority: P1) 🎯 MVP READY

**Goal**: Implement MCP 2025 OAuth 2.1 compliant JWT validation with JWKS, enhanced with all security fixes from previous user stories

**Independent Test**: Configure JWKS endpoint, issue valid JWT from OAuth provider, verify authenticated requests succeed and invalid tokens return HTTP 401

### Tests for User Story 1 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T076 [P] [US1] Write test_jwt_valid_token_accepted() in tests/unit/test_token_verification_basic.py - verify valid JWT with correct iss/aud/exp is accepted
- [ ] T077 [P] [US1] Write test_jwt_expired_token_rejected() in tests/unit/test_token_verification_basic.py - verify expired JWT returns HTTP 401
- [ ] T078 [P] [US1] Write test_jwt_wrong_audience_rejected() in tests/unit/test_token_verification_basic.py - verify incorrect aud returns HTTP 401 with generic message
- [ ] T079 [P] [US1] Write test_jwt_insufficient_scopes() in tests/unit/test_token_verification_basic.py - verify missing required scopes returns HTTP 403
- [ ] T080 [P] [US1] Write test_jwks_key_rotation() in tests/integration/test_oauth21_compliance.py - mock JWKS endpoint, rotate keys, verify new tokens validated
- [ ] T081 [P] [US1] Write test_clock_skew_tolerance() in tests/unit/test_token_verification_basic.py - verify 60s clock skew allowed, 120s+ rejected
- [ ] T082 [P] [US1] Write test_generic_error_messages() in tests/unit/test_https_enforcement.py - verify error responses don't leak expected issuer/audience

### Implementation for User Story 1

- [ ] T083 [P] [US1] Add validate_https_jwks() field validator to JWTVerifierConfig in src/models/auth.py enforcing HTTPS (except localhost in dev)
- [ ] T084 [P] [US1] Update JWTVerifier in src/auth/jwt.py to use PyJWT's JWT verification options dict with verify_signature=True, verify_exp=True, verify_aud=True, verify_iss=True
- [ ] T085 [P] [US1] Update JWT exception handling in JWTVerifier.verify() in src/auth/jwt.py to return generic client errors while logging detailed server errors
- [ ] T086 [P] [US1] Add scope validation to JWTVerifier.verify() in src/auth/jwt.py using verify_scopes() method from base class
- [ ] T087 [P] [US1] Update clock_skew field constraint in JWTVerifierConfig in src/models/auth.py to le=120 (reduced from 300)
- [ ] T088 [US1] Update all JWT error handling in src/auth/jwt.py to log detailed errors with logger.warning() and return ValidationResult.failure_result() with generic messages
- [ ] T089 [US1] Add _extract_claims() method enhancement in JWTVerifier in src/auth/jwt.py to handle both space-separated and list scopes
- [ ] T090 [US1] Verify JWTVerifier uses hash_token() in all log statements (should already be done in T052)
- [ ] T091 [US1] Run all US1 tests and verify they now pass (pytest tests/unit/test_token_verification_basic.py tests/integration/test_oauth21_compliance.py tests/unit/test_https_enforcement.py -v)

**Checkpoint**: JWT with JWKS fully functional, all security hardening applied, MCP 2025 compliant - **MVP READY FOR DEPLOYMENT**

---

## Phase 7: User Story 4 - OAuth 2.0 Token Introspection (Priority: P2)

**Goal**: Support RFC 7662 opaque token validation for enterprise OAuth servers (Auth0, Okta)

**Independent Test**: Configure introspection endpoint with client credentials, issue opaque token, verify server calls endpoint and handles active/inactive responses

### Tests for User Story 4 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T092 [P] [US4] Write test_introspection_active_token() in tests/unit/test_token_verification_basic.py - mock introspection returning active=true, verify token accepted
- [ ] T093 [P] [US4] Write test_introspection_inactive_token() in tests/unit/test_token_verification_basic.py - mock introspection returning active=false, verify HTTP 401
- [ ] T094 [P] [US4] Write test_introspection_timeout() in tests/unit/test_token_verification_basic.py - mock slow endpoint, verify timeout returns HTTP 500
- [ ] T095 [P] [US4] Write test_introspection_client_secret_masked() in tests/unit/test_secret_manager.py - verify SecretStr prevents logging of client_secret
- [ ] T096 [P] [US4] Write test_introspection_https_enforcement() in tests/unit/test_https_enforcement.py - verify http:// URLs rejected in production

### Implementation for User Story 4

- [ ] T097 [P] [US4] Add validate_https_introspection() field validator to IntrospectionVerifierConfig in src/models/auth.py enforcing HTTPS (except localhost in dev)
- [ ] T098 [P] [US4] Verify IntrospectionTokenVerifier uses SecretStr for client_secret (should already be done in T069-T070)
- [ ] T099 [P] [US4] Update IntrospectionTokenVerifier.verify() in src/auth/introspection.py to use hash_token() in all log statements (should already be done in T053)
- [ ] T100 [US4] Add timeout parameter to httpx.AsyncClient.post() in IntrospectionTokenVerifier.verify() in src/auth/introspection.py using config.timeout
- [ ] T101 [US4] Update introspection error handling in src/auth/introspection.py to return generic client errors (HTTP 500 with "server_error") while logging detailed server errors
- [ ] T102 [US4] Add scope validation to IntrospectionTokenVerifier.verify() in src/auth/introspection.py using verify_scopes() method
- [ ] T103 [US4] Run all US4 tests and verify they now pass (pytest tests/unit/test_token_verification_basic.py tests/unit/test_secret_manager.py tests/unit/test_https_enforcement.py -k introspection -v)

**Checkpoint**: Introspection support complete, enterprise OAuth integration enabled

---

## Phase 8: User Story 5 - Development Testing Utilities (Priority: P3)

**Goal**: Provide static token mapping and RSA key pair generation for local development with production guards

**Independent Test**: Configure StaticTokenVerifier locally, verify authentication works in development and fails in production with clear error

### Tests for User Story 5 ⚠️ WRITE FIRST, ENSURE THEY FAIL

- [ ] T104 [P] [US5] Write test_static_token_development_only() in tests/unit/test_token_verification_basic.py - verify StaticTokenVerifier works in development
- [ ] T105 [P] [US5] Write test_static_token_production_rejected() in tests/security/test_security_audit_fixes.py - verify ENVIRONMENT=production raises ValidationError
- [ ] T106 [P] [US5] Write test_rsa_keypair_generation() in tests/unit/test_token_verification_basic.py - verify RSAKeyPair.generate() creates valid keys
- [ ] T107 [P] [US5] Write test_rsa_keypair_token_creation() in tests/unit/test_token_verification_basic.py - verify create_token() produces valid JWT
- [ ] T108 [P] [US5] Write test_rsa_private_key_export_blocked_in_prod() in tests/security/test_security_audit_fixes.py - verify private_key_pem property raises error in production

### Implementation for User Story 5

- [ ] T109 [P] [US5] Update StaticTokenVerifierConfig.prevent_production_use() in src/models/auth.py to check multiple production signals (ENVIRONMENT, K_SERVICE, KUBERNETES_SERVICE_HOST)
- [ ] T110 [P] [US5] Add production environment check to RSAKeyPair.private_key_pem property in src/auth/jwt.py raising RuntimeError in production
- [ ] T111 [P] [US5] Verify StaticTokenVerifier uses hash_token() in logs (should already be done in T052)
- [ ] T112 [US5] Add prominent warning logging to StaticTokenVerifier.__init__() in src/auth/jwt.py stating "FOR DEVELOPMENT ONLY"
- [ ] T113 [US5] Add prominent warning logging to RSAKeyPair usage in src/auth/jwt.py when methods are called
- [ ] T114 [US5] Run all US5 tests and verify they now pass (pytest tests/unit/test_token_verification_basic.py tests/security/test_security_audit_fixes.py -k "static_token or rsa_keypair" -v)

**Checkpoint**: Development utilities functional with strong production guards

---

## Phase 9: Integration Testing & MCP 2025 Compliance

**Purpose**: Verify end-to-end OAuth 2.1 Resource Server compliance and all security audit findings fixed

### OAuth 2.1 Compliance Tests

- [ ] T115 [P] Write test_mcp_2025_bearer_token_extraction() in tests/integration/test_oauth21_compliance.py - verify tokens extracted only from Authorization header
- [ ] T116 [P] Write test_mcp_2025_http_401_invalid_token() in tests/integration/test_oauth21_compliance.py - verify HTTP 401 for invalid tokens
- [ ] T117 [P] Write test_mcp_2025_http_403_insufficient_scope() in tests/integration/test_oauth21_compliance.py - verify HTTP 403 for insufficient scopes
- [ ] T118 [P] Write test_mcp_2025_https_enforcement() in tests/integration/test_oauth21_compliance.py - verify HTTPS required for external endpoints in production
- [ ] T119 [P] Write test_oauth21_section_52_compliance() in tests/integration/test_oauth21_compliance.py - verify signature, expiration, audience, issuer validation

### Security Audit Verification Tests

- [ ] T120 [P] Write test_all_critical_vulnerabilities_fixed() in tests/security/test_security_audit_fixes.py - comprehensive test covering SC-001 (algorithm confusion, weak HMAC, token logging, rate limiting)
- [ ] T121 [P] Write test_owasp_api_top10_compliance() in tests/security/test_security_audit_fixes.py - verify SC-003 (authentication controls, no info disclosure)
- [ ] T122 [P] Write test_no_plaintext_tokens_in_logs() in tests/security/test_security_audit_fixes.py - grep all log output, verify zero plaintext tokens (SC-004)
- [ ] T123 [P] Write test_production_environment_guards() in tests/security/test_security_audit_fixes.py - verify SC-007 (StaticTokenVerifier blocked, RSAKeyPair blocked)

### Integration Tests

- [ ] T124 Run all unit tests (pytest tests/unit/ -v) and ensure 100% pass rate
- [ ] T125 Run all integration tests (pytest tests/integration/ -v) and ensure 100% pass rate
- [ ] T126 Run all security tests (pytest tests/security/ -v) and ensure 100% pass rate
- [ ] T127 Run pytest with coverage (pytest --cov=src/auth --cov=src/models/auth --cov-report=html) and verify >=80% line coverage, >=70% branch coverage

**Checkpoint**: All tests passing, security audit findings verified fixed, MCP 2025 compliance confirmed

---

## Phase 10: Documentation & Deployment

**Purpose**: Production deployment preparation and documentation

### Deployment Scripts

- [ ] T128 [P] Implement setup_secrets.sh in scripts/deploy/setup_secrets.sh to create Google Cloud Secret Manager secrets (jwt-issuer, jwt-audience, jwt-jwks-uri, introspection-url, introspection-client-id, introspection-client-secret)
- [ ] T129 [P] Add IAM permission grant commands to setup_secrets.sh for Cloud Run service account (roles/secretmanager.secretAccessor)
- [ ] T130 [P] Add example .env file template to repository root as .env.example with all required environment variables documented

### Code Quality

- [ ] T131 [P] Run ruff check on src/auth/ and src/models/auth.py, fix any linting errors
- [ ] T132 [P] Run mypy on src/auth/ and src/models/auth.py, fix any type errors
- [ ] T133 Update src/auth/__init__.py to export RateLimiter, SecretManager, and all new configuration models

### Documentation Updates

- [ ] T134 [P] Update CLAUDE.md with new dependencies (google-cloud-secret-manager, python-dotenv) using update-agent-context.sh script (should already be done during planning phase)
- [ ] T135 Create README.md in src/auth/ directory documenting the token verification architecture, security features, and configuration options
- [ ] T136 Add inline docstrings to all public methods in RateLimiter class in src/auth/rate_limiter.py
- [ ] T137 Add inline docstrings to all public methods in SecretManager class in src/auth/secrets.py

---

## Phase 11: Final Validation & Security Checklist

**Purpose**: Pre-deployment security checklist and final validation

### Security Checklist Verification

- [ ] T138 Verify ENVIRONMENT=production environment variable configuration in deployment
- [ ] T139 Verify Secret Manager backend configured (FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager)
- [ ] T140 Verify HTTPS enforced for all JWKS and introspection endpoints
- [ ] T141 Verify rate limiting enabled (FASTMCP_SERVER_AUTH_RATE_LIMIT_ENABLED=true)
- [ ] T142 Verify clock skew <=120 seconds
- [ ] T143 Verify no StaticTokenVerifier usage in production code paths
- [ ] T144 Verify Service account IAM permissions configured correctly
- [ ] T145 Verify Cloud Logging enabled for audit trail

### Final Tests

- [ ] T146 Run complete test suite (pytest tests/ -v) and verify 100% pass rate
- [ ] T147 Test with real OAuth provider tokens (Google, Microsoft, or Auth0) using test_server.py
- [ ] T148 Verify secret rotation works by updating a secret in Secret Manager and waiting for TTL expiration (300s)
- [ ] T149 Verify rate limiting works by sending 11 rapid requests with curl and confirming 11th returns HTTP 429
- [ ] T150 Verify no tokens appear in logs by grepping server output for token patterns

**Checkpoint**: Production ready - all security requirements met, all tests passing, deployment scripts ready

---

## Dependencies & Parallel Execution

### User Story Completion Order

```
Foundation (Phase 2) - MUST complete first
    ↓
┌──────────────────────────────────────────────────┐
│ Can implement in parallel (all are P1/P2/P3):    │
│                                                   │
│ • US3: Algorithm Confusion (Phase 3)             │
│ • US6: Rate Limiting (Phase 4)                   │
│ • US2: Secret Management (Phase 5)               │
│ • US1: JWT with JWKS (Phase 6) - MVP candidate   │
│ • US4: Introspection (Phase 7)                   │
│ • US5: Dev Utilities (Phase 8)                   │
└──────────────────────────────────────────────────┘
    ↓
Integration & Compliance (Phase 9)
    ↓
Documentation & Deployment (Phase 10)
    ↓
Final Validation (Phase 11)
```

### Parallel Execution Examples

**Phase 2** (Foundational):
- T013-T015 (models) can run in parallel
- T018-T020 (rate limit models) can run in parallel with T021-T025 (secret models)

**Phase 3** (Algorithm Confusion):
- T026-T031 (all tests) can run in parallel
- T032-T036 (all implementation) can run in parallel after tests written

**Phase 4** (Rate Limiting):
- T038-T043 (all tests) can run in parallel
- T044-T046 (RateLimiter class) can run in parallel
- T052-T054 (logging updates) can run in parallel

**Phase 5** (Secret Management):
- T057-T062 (all tests) can run in parallel
- T063-T068 (SecretManager class) can run in parallel
- T069-T070 (SecretStr updates) can run in parallel with T071-T074 (config loaders)

**Phases 3-8**: Can be developed by independent teams simultaneously since each user story is self-contained

**Phase 9**: All integration tests (T115-T123) can run in parallel

**Phase 10**: Documentation tasks (T128-T137) can run in parallel with final cleanup

---

## Implementation Strategy

### MVP Scope (Recommended First Delivery)

**Minimum Viable Product** = User Story 1 (JWT with JWKS) + All security fixes from US3 and US6:

- Phase 1: Setup (T001-T012)
- Phase 2: Foundation (T013-T025)
- Phase 3: Algorithm Confusion Protection (T026-T037) - CRITICAL
- Phase 4: Rate Limiting (T038-T056) - CRITICAL
- Phase 6: JWT with JWKS (T076-T091) - MVP CORE
- Phase 9: Integration Tests (T115-T127)
- Phase 11: Final Validation (T138-T150)

**MVP Delivers**:
- ✅ MCP 2025 OAuth 2.1 compliant JWT validation
- ✅ Algorithm confusion vulnerability fixed
- ✅ Rate limiting active
- ✅ Token hashing in logs
- ✅ Production ready with security hardening

### Incremental Delivery Plan

1. **Sprint 1** (MVP): Foundation + US3 + US6 + US1 (85 tasks)
2. **Sprint 2** (Secret Manager): US2 (19 tasks)
3. **Sprint 3** (Introspection): US4 (12 tasks)
4. **Sprint 4** (Dev Tools): US5 (11 tasks)
5. **Sprint 5** (Polish): Phase 10-11 documentation and final validation (23 tasks)

**Total**: 150 tasks across 11 phases

---

## Task Summary

### Total Tasks: 150

**By Phase**:
- Phase 1 (Setup): 12 tasks
- Phase 2 (Foundation): 13 tasks
- Phase 3 (US3 - Algorithm Confusion): 12 tasks (6 tests + 6 implementation)
- Phase 4 (US6 - Rate Limiting): 19 tasks (6 tests + 13 implementation)
- Phase 5 (US2 - Secret Management): 19 tasks (6 tests + 13 implementation)
- Phase 6 (US1 - JWT JWKS): 16 tasks (7 tests + 9 implementation) 🎯 MVP
- Phase 7 (US4 - Introspection): 12 tasks (5 tests + 7 implementation)
- Phase 8 (US5 - Dev Utilities): 11 tasks (5 tests + 6 implementation)
- Phase 9 (Integration): 13 tasks
- Phase 10 (Documentation): 10 tasks
- Phase 11 (Final Validation): 13 tasks

**By User Story**:
- US1 (JWT JWKS): 16 tasks
- US2 (Secret Management): 19 tasks
- US3 (Algorithm Confusion): 12 tasks
- US4 (Introspection): 12 tasks
- US5 (Dev Utilities): 11 tasks
- US6 (Rate Limiting): 19 tasks
- Foundation: 25 tasks
- Integration/Testing: 26 tasks
- Documentation: 10 tasks

**Parallelizable Tasks**: 92 tasks marked with [P] can run in parallel

**Independent Testing**:
- Each user story (US1-US6) has explicit independent test criteria
- All tests follow TDD approach (write first, ensure fail, implement, verify pass)
- 100% test coverage required for security-critical code paths

---

## Format Validation

✅ All tasks follow strict checklist format:
- ✅ Checkbox prefix: `- [ ]`
- ✅ Task ID: Sequential (T001-T150)
- ✅ [P] marker: 92 tasks parallelizable
- ✅ [Story] label: All user story tasks labeled (US1-US6)
- ✅ File paths: Included in all implementation task descriptions
- ✅ Dependencies: Clear phase order with foundational blocking

**Ready for `/speckit.implement` execution** 🚀
