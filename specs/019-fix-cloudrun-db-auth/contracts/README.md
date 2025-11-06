# API Contracts

**Feature**: 019-fix-cloudrun-db-auth
**Date**: 2025-11-06

## No Contract Changes

This feature is an **internal implementation fix** to the database connection layer. It does NOT modify any public APIs or contracts.

### Unchanged Public Interfaces

1. **MCP Tools** (`src/tools/`):
   - `search_hansard_speeches` - No signature changes
   - `fetch_hansard_speech` - No signature changes
   - `ingest_hansard_speech` - No signature changes

2. **Vector Store Service** (`src/storage/postgres_vector_store.py`):
   - `PostgresVectorStoreService.__init__()` - No signature changes
   - `add_chunks()` - No signature changes
   - `similarity_search()` - No signature changes
   - `delete()` - No signature changes

3. **Metadata Store** (`src/storage/metadata_store.py`):
   - `SpeechMetadataStore` - No changes

4. **FastMCP Server** (`src/server.py`):
   - All tool endpoints unchanged
   - SSE transport unchanged
   - OAuth authentication unchanged

### Internal Changes Only

**Modified**: `src/storage/cloud_sql_engine.py`

**Added Internal Properties** (for testing/debugging):
- `detected_iam_user` (read-only property): Returns detected IAM principal email
- `detection_method` (read-only property): Returns detection method used
- `iam_valid` (read-only property): Returns whether IAM user is valid

**Purpose**: Enable testing and debugging of IAM detection without changing public behavior.

**Backward Compatibility**: ✅ 100% backward compatible
- Existing code using `CloudSQLEngine` continues working unchanged
- New properties are optional (read-only, no breaking changes)
- Existing tests pass without modification (10/10 baseline)

### API Contract Validation

**Test Suite**: `tests/test_full_ingestion_tdd.py`

**Validation**:
```bash
# All existing tests must pass without modification
pytest tests/test_full_ingestion_tdd.py -v
# Expected: 10 passed
```

**Success Criteria**:
- No MCP tool signatures changed
- No database schema changes
- No breaking changes to `PostgresVectorStoreService` or `SpeechMetadataStore`
- 100% backward compatibility maintained

---

## Debug Endpoint (Existing)

**Endpoint**: `/debug/iam-user`
**Method**: GET
**Authorization**: Required (Bearer token)

**Purpose**: Troubleshooting IAM detection in Cloud Run

**Response Schema**:
```json
{
  "detected_iam_user": "string",
  "detection_method": "METADATA_SERVICE | ADC_CREDENTIALS | GCLOUD_CONFIG | FALLBACK",
  "iam_valid": "boolean",
  "environment": "cloud_run | local",
  "k_service": "string | null",
  "connection_test": "SUCCESS | FAILED"
}
```

**Example**:
```json
{
  "detected_iam_user": "666924716777-compute@developer.gserviceaccount.com",
  "detection_method": "METADATA_SERVICE",
  "iam_valid": true,
  "environment": "cloud_run",
  "k_service": "hansard-mcp-server",
  "connection_test": "SUCCESS"
}
```

**Status**: Already implemented (no changes needed, just documentation)

---

**Contracts Complete** - No API changes required for this feature.
