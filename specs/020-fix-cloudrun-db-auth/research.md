# Research: Cloud Run IAM Authentication for Cloud SQL

**Feature**: 019-fix-cloudrun-db-auth
**Date**: 2025-11-06
**Status**: Complete

## Overview

This document consolidates research findings on how to properly detect IAM principals in Cloud Run vs local development environments for Cloud SQL PostgreSQL authentication.

---

## 1. IAM User Detection in Cloud Run

### Question
How to detect service account from Cloud Run metadata service? What's the API endpoint and format? How does it differ from local ADC file parsing?

### Decision
Use a **three-tier fallback strategy** for IAM user detection:
1. **Cloud Run metadata service** (highest priority)
2. **Application Default Credentials (ADC)** parsing
3. **gcloud CLI config** (local development fallback)

### Rationale

**Cloud Run Metadata Service** (Priority 1):
- Endpoint: `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email`
- Header required: `Metadata-Flavor: Google`
- Returns: Plain text service account email (e.g., `666924716777-compute@developer.gserviceaccount.com`)
- Detection: Check for `K_SERVICE` environment variable (set by Cloud Run)
- Timeout: 1 second (fast-fail if not in Cloud Run)
- **Most reliable** in Cloud Run environment

**Application Default Credentials** (Priority 2):
- Uses `google.auth.default()` to load credentials
- Service account credentials expose `service_account_email` or `_service_account_email` attribute
- Works in both Cloud Run and local development (with `gcloud auth application-default login`)
- **Issue**: Sometimes returns `"default"` placeholder instead of actual email
- **Workaround**: Filter out `"default"` and try next method

**gcloud CLI Config** (Priority 3):
- Command: `gcloud config get-value account`
- Returns: User or service account email from active gcloud configuration
- Works in local development with `gcloud auth login`
- **Slowest** (subprocess call ~100ms)
- **Not available** in Cloud Run containers

### Alternatives Considered

❌ **Environment variable only** (`CLOUDSQL_USER`):
- Rejected: Requires manual configuration, error-prone
- Cloud Run should auto-detect service account

❌ **Single method** (metadata service only):
- Rejected: Breaks local development
- Need fallback for developers without K_SERVICE

❌ **Hard-coded service account**:
- Rejected: Violates security best practices
- Breaks multi-environment deployments

### Implementation Reference

Current code in [cloud_sql_engine.py:180-229](src/storage/cloud_sql_engine.py#L180-229):

```python
# Priority 1: Try metadata server (Cloud Run)
if os.getenv('K_SERVICE'):
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers, timeout=1)
    if response.status_code == 200:
        iam_user = response.text.strip()

# Priority 2: Try default credentials
if not iam_user:
    credentials, project = google.auth.default()
    if hasattr(credentials, 'service_account_email'):
        email = credentials.service_account_email
        if email and email != "default":
            iam_user = email

# Priority 3: gcloud config (local dev)
if not iam_user:
    result = subprocess.check_output(['gcloud', 'config', 'get-value', 'account'])
    if result and '@' in result:
        iam_user = result
```

**Issue**: The `"default"` filter may be preventing Cloud Run from using ADC properly.

---

## 2. Cloud SQL Connector IAM Auth

### Question
How does cloud-sql-python-connector handle IAM auth with pg8000? What's the correct way to pass service account email as database user? Are there known issues with version <1.10.0?

### Decision
Use **manual OAuth2 token fetching** as primary method, with `enable_iam_auth=True` as fallback.

### Rationale

**Cloud SQL Connector v1.10.0+ Behavior**:
- Supports two IAM auth modes:
  1. **enable_iam_auth=True**: Connector manages token refresh automatically
  2. **Manual token**: Pass OAuth2 access token as password, user as service account email

**Version History**:
- v1.4.0-1.7.0: Unstable IAM auth, known `NoneType.decode()` errors
- v1.8.0+: Stable IAM auth with pg8000 driver
- v1.10.0+: **Recommended** (improved error messages, better token refresh)
- Upgraded in main commit (3ba327d): `cloud-sql-python-connector>=1.10.0`

**pg8000 Driver Requirements**:
- ONLY driver supporting IAM auth with Cloud SQL Connector
- Expects `user` parameter (service account email)
- Expects `password` parameter (OAuth2 token or managed by connector)
- **Critical**: `password=None` causes `NoneType.decode()` error in some versions

### Alternatives Considered

❌ **psycopg3 driver**:
- Rejected: Cloud SQL Connector v1.18+ doesn't support IAM auth with psycopg
- Only pg8000 supported for IAM

❌ **enable_iam_auth=True only**:
- Rejected: Less control over token refresh
- Manual token fetch provides better error messages

❌ **Password auth**:
- Rejected: Violates constitution (Section IV: Security by Default)
- Credentials must never be embedded

### Implementation Reference

Current code in [cloud_sql_engine.py:236-250](src/storage/cloud_sql_engine.py#L236-250):

```python
# Manual OAuth2 token fetch (primary method)
try:
    credentials, _ = google.auth.default()
    if not getattr(credentials, "valid", False):
        credentials.refresh(GoogleAuthRequest())
    token = getattr(credentials, "token", None)
    if not token:
        raise RuntimeError("Failed to obtain IAM access token")
    kwargs["password"] = token
except Exception as e:
    # Fallback to connector-managed IAM auth
    kwargs["enable_iam_auth"] = True
    logging.warning(f"Manual token fetch failed: {e}")
```

**Best Practice**: Use manual token fetch to avoid `password=None` scenarios.

---

## 3. Error Patterns

### Question
Why does `user="default"` appear in Cloud Run? What causes "NoneType has no attribute 'decode'" error? How to distinguish transient vs permanent auth failures?

### Root Cause Analysis

**`user="default"` Error**:
- **Cause**: ADC credentials object has `service_account_email="default"` placeholder
- **Location**: [cloud_sql_engine.py:203](src/storage/cloud_sql_engine.py#L203)
- **Current behavior**: Code filters out `"default"`, but may fail to detect real email
- **Fix needed**: Improve detection logic or rely more on metadata service

**`NoneType.decode()` Error**:
- **Cause**: pg8000 driver receives `password=None` and tries to decode it
- **Versions affected**: cloud-sql-python-connector <1.10.0
- **Mitigation**:
  1. Upgraded to >=1.10.0 (done in main)
  2. Manual token fetch ensures password is always set
  3. `create_extension=False` prevents privilege errors that trigger this path

**Transient vs Permanent Failures**:

| Error Type | Pattern | Classification | Retry? |
|-----------|---------|----------------|--------|
| Connection timeout | `OperationalError: timeout` | Transient | Yes (3x, exponential backoff) |
| Token expired | `401 Unauthorized` | Transient | Yes (auto-refresh token) |
| Metadata unavailable | `requests.ConnectionError` | Transient | Yes (fallback to ADC) |
| Missing IAM role | `403 Forbidden` | Permanent | No (fail fast, log error) |
| Wrong database user | `FATAL: role ... does not exist` | Permanent | No (fail fast, suggest fix) |
| Extension not enabled | `RuntimeError: pgvector extension` | Permanent | No (already validated, clear message) |

### Decision
Implement **fail-fast with clear messages** for permanent errors, **retry with exponential backoff** for transient errors.

### Implementation Reference

Existing retry logic in [postgres_vector_store.py:120-188](src/storage/postgres_vector_store.py#L120-188):

```python
@with_retry(max_retries=3, base_delay=1.0)
async def add_chunks(...):
    # Auto-retries OperationalError with 1s, 2s, 4s backoff
```

**Needed**: Add IAM-specific error detection and logging.

---

## 4. Testing Strategy

### Question
How to mock Cloud Run metadata service for local tests? How to test IAM auth without actual Cloud Run deployment? How to preserve existing 10/10 test pass rate?

### Decision
Use **pytest fixtures with environment mocking** and **integration tests with real Cloud SQL**.

### Test Strategy

**Unit Tests** (test_cloud_run_iam_auth.py):
- Mock `K_SERVICE` environment variable
- Mock `requests.get()` for metadata service
- Mock `google.auth.default()` for ADC
- Verify correct IAM user detection in each scenario
- **No real database** - test detection logic only

**Integration Tests** (test_local_iam_auth.py):
- Use real Cloud SQL connection with IAM auth
- Verify actual authentication succeeds
- Test connection pooling and token refresh
- **Requires**: Local credentials (`gcloud auth application-default login`)

**Regression Tests** (test_full_ingestion_tdd.py):
- **Existing**: 10 tests, 100% pass rate
- **Baseline**: Must continue passing after changes
- **Coverage**: Full ingestion, search, fetch workflows
- **Environment**: Local development with IAM auth

### Test Fixtures

```python
# Mock Cloud Run environment
@pytest.fixture
def mock_cloud_run_metadata(monkeypatch, requests_mock):
    monkeypatch.setenv('K_SERVICE', 'test-service')
    requests_mock.get(
        'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email',
        text='test-service-account@project.iam.gserviceaccount.com'
    )

# Mock local ADC
@pytest.fixture
def mock_local_adc(monkeypatch):
    # Mock google.auth.default() to return test credentials
    pass
```

### Alternatives Considered

❌ **Only integration tests**:
- Rejected: Too slow, requires Cloud SQL access
- Unit tests provide fast feedback

❌ **Mock database connections**:
- Rejected: Doesn't test actual IAM auth
- Need real connection to verify token exchange

❌ **Skip existing tests**:
- Rejected: Violates constitution (Test-First Quality Gates)
- Must maintain 10/10 pass rate

### Validation Checklist

- [ ] Unit tests pass for Cloud Run metadata service detection
- [ ] Unit tests pass for local ADC detection
- [ ] Integration tests connect successfully with IAM auth
- [ ] Existing test_full_ingestion_tdd.py maintains 10/10 pass rate
- [ ] Cloud Run deployment connects successfully
- [ ] Debug endpoint returns correct service account email

---

## 5. Best Practices Summary

### IAM Authentication
1. **Always use metadata service first** in Cloud Run (check `K_SERVICE`)
2. **Filter "default" placeholder** from ADC credentials
3. **Fetch OAuth2 token manually** to avoid `password=None`
4. **Log IAM user at INFO level** for troubleshooting

### Error Handling
1. **Validate pgvector extension** before connecting (already implemented)
2. **Fail fast** with clear messages for permanent errors
3. **Retry with exponential backoff** for transient errors
4. **Log connection parameters** (non-sensitive) for debugging

### Testing
1. **Write tests first** (TDD approach per constitution)
2. **Mock metadata service** for unit tests
3. **Use real Cloud SQL** for integration tests
4. **Preserve baseline** (10/10 test pass rate)

### Configuration
1. **No passwords** in environment variables
2. **Detect environment automatically** (Cloud Run vs local)
3. **Use safe defaults** (IAM auth, no password)
4. **Log configuration** at startup

---

## Next Steps

1. **Phase 1: Design**
   - Generate data-model.md (connection state model)
   - Generate quickstart.md (testing guide)
   - Update CLAUDE.md with learnings

2. **Phase 2: Tasks**
   - Generate tasks.md with TDD workflow
   - Implement IAM detection improvements
   - Write and run tests
   - Validate Cloud Run deployment

3. **Phase 3: Implementation**
   - Fix IAM user detection logic
   - Add comprehensive logging
   - Deploy and validate
   - Update documentation

---

**Research Complete** - Ready for Phase 1 design artifacts.
